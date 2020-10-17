#include<string.h>
#include<arpa/inet.h>
#include<stdlib.h>
#include<time.h>

#include "lcp.h"
#include "debug.h"
#include "pppoe.h"
#include "netif.h"

static struct ixc_lcp lcp;
static unsigned int server_magic_num=0;

static void ixc_lcp_neg_send(unsigned char code,unsigned char id,unsigned char type,unsigned char length,void *data,unsigned int magic_num);
static void ixc_lcp_neg_send_for_pap(unsigned char code,unsigned char id,unsigned int magic_num);
static void ixc_lcp_neg_send_for_chap(unsigned char code,unsigned char id,unsigned int magic_num);
static void ixc_lcp_neg_request_send_auto(void);

static unsigned int ixc_lcp_rand_magic_num(void)
{
    unsigned int rand_no;
    srand(time(NULL));

    rand_no=rand();

    return rand_no;
}

/// reserved 选项那么什么都不处理
static void ixc_lcp_opt_reserved_cb(struct ixc_mbuf *m,unsigned char code,unsigned char id,struct ixc_lcp_opt *opt)
{
    return;
}

static void ixc_lcp_opt_max_recv_unit_cb(struct ixc_mbuf *m,unsigned char code,unsigned char id,struct ixc_lcp_opt *opt)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    unsigned short mru;

    if(code==IXC_LCP_CFG_ACK){
        DBG("MRU Neg OK\r\n");
        lcp.mru_neg_ok=1;
        return;
    }
    
    // 所有的PPPoE服务器应该都支持MRU
    if(code==IXC_LCP_CFG_REJECT){
        STDERR("bug,PPPoE Server LCP unsupport MRU\r\n");
        ixc_pppoe_reset();
        return;
    }

    // 处理LCP MRU 请求
    // 检查MRU长度是否合法
    if(opt->length!=2){
        STDERR("bug,Wrong PPPoE Server MRU length\r\n");
        return;
    }

    memcpy(&mru,opt->data,2);
    mru=ntohs(mru);

    // 检查是否允许的MRU范围
    if(mru<568 || mru>1492){
        mru=htons(1492);
        ixc_lcp_neg_send(IXC_LCP_CFG_NAK,id,IXC_LCP_OPT_TYPE_MAX_RECV_UNIT,2,&mru,server_magic_num);
        return;
    }

    netif->mtu_v4=mru;
    netif->mtu_v6=mru;

    mru=htons(mru);
    ixc_lcp_neg_send(IXC_LCP_CFG_ACK,id,IXC_LCP_OPT_TYPE_MAX_RECV_UNIT,2,&mru,server_magic_num);
}   

static void ixc_lcp_opt_auth_proto_cb(struct ixc_mbuf *m,unsigned char code,unsigned char id,struct ixc_lcp_opt *opt)
{
    int is_pap=0,is_chap=0;
    unsigned char buf[512];
    unsigned int magic_num=ixc_lcp_rand_magic_num();

    // 检查长度是否合法
    if(opt->length<2){
        DBG("PPPoE Server LCP auth data format error %d\r\n",opt->length);
        return;
    }

    // 处理配置拒绝的问题
    if(code==IXC_LCP_CFG_REJECT){
        STDERR("bug,PPPoE Server LCP unsupport PAP or CHAP\r\n");
        return;
    }
    // 处理验证请求
    if(opt->data[0]==0xc0 && opt->data[1]==0x23) is_pap=1;
    if(opt->data[0]==0xc2 && opt->data[1]==0x23) is_chap=1;

    // 不是PAP和CHAP认证协议发送错误
    if(!is_pap && !is_chap){
        DBG("unsupport pppoe Server auth method\r\n");
        return;
    }

    if(is_chap && opt->length!=3){
        DBG("PPPoE Server LCP auth data format error\r\n");
        return;
    }

    // 验证协议握手成功的处理方式
    if(code==IXC_LCP_CFG_ACK){
        DBG("Auth Neg OK\r\n");

        if(is_chap) lcp.is_chap=1;
        else lcp.is_pap=1;

        lcp.auth_neg_ok=1;
        return;
    }

    if(code==IXC_LCP_CFG_NAK){
        lcp.magic_num=magic_num;

        if(is_pap){
            lcp.is_chap=-1;
            lcp.is_pap=0;
            ixc_lcp_neg_send_for_pap(IXC_LCP_CFG_REQ,1,magic_num);
        }else{
            lcp.is_chap=0;
            lcp.is_pap=-1;
            ixc_lcp_neg_send_for_chap(IXC_LCP_CFG_REQ,1,magic_num);
        }
        return;
    }

    if(is_chap) {
        lcp.is_pap=-1;
    }else{
        lcp.is_chap=-1;
    }

    memcpy(buf,opt->data,opt->length);
    ixc_lcp_neg_send(IXC_LCP_CFG_ACK,id,IXC_LCP_OPT_TYPE_AUTH_PROTO,opt->length,buf,server_magic_num);
}

static void ixc_lcp_opt_qua_proto_cb(struct ixc_mbuf *m,unsigned char code,unsigned char id,struct ixc_lcp_opt *opt)
{
    unsigned char buf[512];
    memcpy(buf,opt->data,opt->length);

    if(code==IXC_LCP_CFG_REQ){
        ixc_lcp_neg_send(IXC_LCP_CFG_REJECT,id,IXC_LCP_OPT_TYPE_ADDR_CTL_COMP,opt->length,buf,server_magic_num);
        return;
    }
}

static void ixc_lcp_opt_proto_comp_cb(struct ixc_mbuf *m,unsigned char code,unsigned char id,struct ixc_lcp_opt *opt)
{
    unsigned char buf[512];
    memcpy(buf,opt->data,opt->length);

    if(code==IXC_LCP_CFG_REQ){
        ixc_lcp_neg_send(IXC_LCP_CFG_REJECT,IXC_LCP_OPT_TYPE_ADDR_CTL_COMP,id,opt->length,buf,server_magic_num);
        return;
    }
}

static void ixc_lcp_opt_addr_ctl_comp_cb(struct ixc_mbuf *m,unsigned char code,unsigned char id,struct ixc_lcp_opt *opt)
{
    unsigned char buf[512];
    memcpy(buf,opt->data,opt->length);

    if(code==IXC_LCP_CFG_REQ){
        ixc_lcp_neg_send(IXC_LCP_CFG_REJECT,id,IXC_LCP_OPT_TYPE_ADDR_CTL_COMP,opt->length,buf,server_magic_num);
        return;
    }
}

static ixc_lcp_opt_cb lcp_opt_cb_set[16];

/// 发送LCP数据包
static void ixc_lcp_send(unsigned short ppp_protoco,unsigned char code,unsigned char id,unsigned short length,void *data)
{
    unsigned char tmp[2048];
    unsigned short *x=(unsigned short *)(&tmp[2]);
    *x=htons(4+length);

    tmp[0]=code;
    tmp[1]=id;

    memcpy(&tmp[4],data,length);
    ixc_pppoe_send_session_packet(ppp_protoco,length+4,tmp);
}

/// 获取配置
static unsigned int ixc_lcp_cfg_magic_get(struct ixc_lcp_opt *first_opt)
{
    struct ixc_lcp_opt *opt=first_opt;
    unsigned int magic_num=0;

    while(NULL!=opt){
        if(opt->type==IXC_LCP_OPT_TYPE_MAGIC_NUM){
            if(opt->length!=4){
                DBG("Wrong magic num length\r\n");
                break;
            }
            memcpy(&magic_num,opt->data,4);
            magic_num=ntohl(magic_num);
            break;
        }
        opt=opt->next;
    }

    return magic_num;
}

/// 解析LCP的选项
static int ixc_lcp_parse_opts(void *data,unsigned short tot_length,struct ixc_lcp_opt **first_opt)
{
    struct ixc_lcp_opt *opt,*first=NULL,*cur;
    unsigned char *ptr=data;
    unsigned short cur_size=0,t;
    struct ixc_lcp_opt_header *h;
    int rs=0;

    // 这里初始化first_opt,避免调用者未初始化调用free_opts可能导致的内存错误
    *first_opt=first;

    while(1){
        if(cur_size==tot_length) break;
        h=(struct ixc_lcp_opt_header *)(ptr+cur_size);

        if(h->length<2){
            DBG("Wrong lcp option length value\r\n");
            rs=-1;
            break;
        }

        t=cur_size+h->length;

        if(t>tot_length){
            DBG("wrong lcp option length\r\n");
            rs=-1;
            break;
        }

        opt=malloc(sizeof(struct ixc_lcp_opt));

        if(NULL==opt){
            STDERR("no memory for struct ixc_lcp_opt\r\n");
            rs=-1;
            break;
        }

        bzero(opt,sizeof(struct ixc_lcp_opt));

        opt->type=h->type;
        // 这里要减去头部长度
        opt->length=h->length-2;

        memcpy(opt->data,ptr+cur_size+2,h->length-2);

        if(NULL==first) first=opt; 
        else cur->next=opt;

        cur=opt;

        cur_size=cur_size+h->length;
    }

    *first_opt=first;

    return rs;
}

static void ixc_lcp_free_opts(struct ixc_lcp_opt *first)
{
    struct ixc_lcp_opt *t,*opt=first;

    while(NULL!=opt){
        t=opt->next;
        free(opt);
        opt=t;
    }
}

static void ixc_lcp_handle_echo_req(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{
    ixc_lcp_send(0xc021,IXC_LCP_ECHO_REPLY,id,length,m->data+m->offset);
}

static void ixc_lcp_handle_echo_reply(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{

}

static void ixc_lcp_handle_term_req(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{
    ixc_lcp_send(0xc021,IXC_LCP_TERM_ACK,id,length,m->data+m->offset);
    ixc_pppoe_reset();
}

static void ixc_lcp_handle_term_ack(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{
}

/// 处理配置函数,包括配置请求,配置NAK以及配置ACK
static void ixc_Lcp_handle_cfg(struct ixc_mbuf *m,unsigned char code,unsigned char id,unsigned short length)
{
    struct ixc_lcp_opt *first_opt=NULL,*opt;
    int rs=ixc_lcp_parse_opts(m->data+m->offset,length,&first_opt);
    unsigned int magic_num=0;

    if(rs<0){
        ixc_lcp_free_opts(first_opt);
        DBG("cannot parse lcp configure options\r\n");
        return;
    }

    magic_num=ixc_lcp_cfg_magic_get(first_opt);

    // 检查magic number是否合法
    if(code==IXC_LCP_CFG_REJECT || code==IXC_LCP_CFG_ACK){
        if(magic_num!=lcp.magic_num){
            DBG("Wrong magic num for code %d\r\n",code);
            ixc_lcp_free_opts(first_opt);
            return;
        }
    }

    opt=first_opt;
    server_magic_num=magic_num;

    while(NULL!=opt){
        switch(opt->type){
            case IXC_LCP_OPT_TYPE_RESERVED:
            case IXC_LCP_OPT_TYPE_MAX_RECV_UNIT:
            case IXC_LCP_OPT_TYPE_AUTH_PROTO:
            case IXC_LCP_OPT_TYPE_QUA_PROTO:
            case IXC_LCP_OPT_TYPE_PROTO_COMP:
            case IXC_LCP_OPT_TYPE_ADDR_CTL_COMP:
                lcp_opt_cb_set[opt->type](m,code,id,opt);
                break;
            // 针对magic num直接跳过
            case IXC_LCP_OPT_TYPE_MAGIC_NUM:
                break;
            default:
                break;
        }
        //DBG("type:%d  length:%d\r\n",opt->type,opt->length);
        opt=opt->next;
    }

    ixc_lcp_free_opts(first_opt);
}

int ixc_lcp_init(void)
{
    bzero(&lcp,sizeof(struct ixc_lcp));
    bzero(lcp_opt_cb_set,sizeof(NULL)*16);

    lcp_opt_cb_set[IXC_LCP_OPT_TYPE_RESERVED]=ixc_lcp_opt_reserved_cb;
    lcp_opt_cb_set[IXC_LCP_OPT_TYPE_MAX_RECV_UNIT]=ixc_lcp_opt_max_recv_unit_cb;
    lcp_opt_cb_set[IXC_LCP_OPT_TYPE_AUTH_PROTO]=ixc_lcp_opt_auth_proto_cb;
    lcp_opt_cb_set[IXC_LCP_OPT_TYPE_QUA_PROTO]=ixc_lcp_opt_qua_proto_cb;
    lcp_opt_cb_set[IXC_LCP_OPT_TYPE_PROTO_COMP]=ixc_lcp_opt_proto_comp_cb;
    lcp_opt_cb_set[IXC_LCP_OPT_TYPE_ADDR_CTL_COMP]=ixc_lcp_opt_addr_ctl_comp_cb;

    return 0;
}

void ixc_lcp_uninit(void)
{

}

void ixc_lcp_handle(struct ixc_mbuf *m)
{
    struct ixc_lcp_cfg_header *lcp_header=(struct ixc_lcp_cfg_header *)(m->data+m->offset);
    unsigned short length=ntohs(lcp_header->length);
    int flags=0;

    if(m->tail-m->offset!=length){
        ixc_mbuf_put(m);
        DBG("Wrong LCP length value\r\n");
        return;
    }

    if(length<6){
        ixc_mbuf_put(m);
        DBG("the LCP length min value is 4\r\n");
        return;
    }

    m->offset+=4;
    length=length-4;

    switch(lcp_header->code){
        case IXC_LCP_CFG_REQ:
        case IXC_LCP_CFG_ACK:
        case IXC_LCP_CFG_NAK:
        case IXC_LCP_CFG_REJECT:
            ixc_Lcp_handle_cfg(m,lcp_header->code,lcp_header->id,length);
            flags=1;
            break;
        case IXC_LCP_TERM_REQ:
            ixc_lcp_handle_term_req(m,lcp_header->id,length);
            break;
        case IXC_LCP_TERM_ACK:
            ixc_lcp_handle_term_ack(m,lcp_header->id,length);
            break;
        case IXC_LCP_CODE_REJECT:
            break;
        case IXC_LCP_PROTO_REJECT:
            break;
        case IXC_LCP_ECHO_REQ:
            ixc_lcp_handle_echo_req(m,lcp_header->id,length);
            break;
        case IXC_LCP_ECHO_REPLY:
            break;
        case IXC_LCP_DISCARD_REQ:
            break;
        default:
            // 注意这里DBG和mbuf_put不能调换顺序,否则可能造成段错误
            DBG("unkown LCP code %d",lcp_header->code);
            break;    
    }
    ixc_mbuf_put(m);
    if(flags) ixc_lcp_neg_request_send_auto();
}

/// 协商请求发送
static void ixc_lcp_neg_send(unsigned char cfg_code,unsigned char id,unsigned char type,unsigned char length,void *data,unsigned int magic_num)
{
    unsigned int rand_no=0;
    unsigned char buf[2048];
    unsigned char types[]={
        type,
        IXC_LCP_OPT_TYPE_MAGIC_NUM
    };
    unsigned char lengths[]={
        length,4
    };
    unsigned char *data_set[2];
    unsigned short size=0;

    lcp.up_time=time(NULL);
    rand_no=htonl(magic_num);

    data_set[0]=data;
    data_set[1]=(unsigned char *)(&rand_no);

    for(int n=0;n<2;n++){
        if(magic_num==0 && n==1) break;
        buf[size]=types[n];
        buf[size+1]=lengths[n]+2;

        memcpy(&buf[size+2],data_set[n],lengths[n]);

        size+=lengths[n]+2;
    }

    ixc_lcp_send(0xc021,cfg_code,id,size,buf);
}

static void ixc_lcp_neg_request_send_for_mru(void)
{
    unsigned short mru=htons(1492);
    unsigned int magic_num=ixc_lcp_rand_magic_num();

    lcp.magic_num=magic_num;

    ixc_lcp_neg_send(IXC_LCP_CFG_REQ,1,IXC_LCP_OPT_TYPE_MAX_RECV_UNIT,2,&mru,magic_num);
}

/// 发送chap验证握手
static void ixc_lcp_neg_send_for_chap(unsigned char code,unsigned char id,unsigned int magic_num)
{
    unsigned char buf[3];

    buf[0]=0xc2;
    buf[1]=0x23;
    buf[2]=0x05;

    ixc_lcp_neg_send(code,id,IXC_LCP_OPT_TYPE_AUTH_PROTO,3,buf,magic_num);
}

/// 发送pap验证握手
static void ixc_lcp_neg_send_for_pap(unsigned char code,unsigned char id,unsigned int magic_num)
{
    unsigned char buf[2];

    buf[0]=0xc0;
    buf[1]=0x23;

    ixc_lcp_neg_send(code,id,IXC_LCP_OPT_TYPE_AUTH_PROTO,2,buf,magic_num); 
}

static void ixc_lcp_neg_request_send_auto(void)
{
    unsigned int magic_num=ixc_lcp_rand_magic_num();

    if(!lcp.mru_neg_ok){
        lcp.magic_num=magic_num;
        ixc_lcp_neg_request_send_for_mru();
        return;
    }

    if(!lcp.auth_neg_ok){
        if(lcp.is_pap==0){
            lcp.magic_num=magic_num;
            ixc_lcp_neg_send_for_pap(IXC_LCP_CFG_REQ,1,magic_num);
            return;
        }

        if(lcp.is_chap==0){
            lcp.magic_num=magic_num;
            ixc_lcp_neg_send_for_chap(IXC_LCP_CFG_REQ,1,magic_num);
            return;
        }

        /// 如果所有验证方式都不支持,那么报告错误并且重置PPPoE
        STDERR("the PPPoE Server cannot support PAP or CHAP auth\r\n");
        ixc_pppoe_reset();
        return;
    }

    if(lcp.is_pap>0) ixc_pppoe_send_pap_user();
}


void ixc_lcp_loop(void)
{
    time_t now=time(NULL);
    if(now-lcp.up_time<3) return;

    ixc_lcp_neg_request_send_auto();
}