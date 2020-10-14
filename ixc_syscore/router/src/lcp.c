#include<string.h>
#include<arpa/inet.h>
#include<stdlib.h>
#include<time.h>

#include "lcp.h"
#include "debug.h"
#include "pppoe.h"
#include "netif.h"

static struct ixc_lcp lcp;

void ixc_lcp_neg_request_send_auto(void);

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

static void ixc_lcp_handle_cfg_request(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{
    struct ixc_lcp_opt *first_opt=NULL,*opt;
    int rs=ixc_lcp_parse_opts(m->data+m->offset,length,&first_opt);
    unsigned short mru,auth_proto;
    int is_error=0;
    unsigned char tmp[512];

    unsigned char ack_packet[2048];
    unsigned short ack_len=0;

    if(rs<0){
        ixc_lcp_free_opts(first_opt);
        DBG("parse lcp option error\r\n");
        return;
    }

    opt=first_opt;
    while(NULL!=opt){
        switch(opt->type){
            case IXC_LCP_OPT_TYPE_MAX_RECV_UNIT:
                if(opt->length!=2){
                    is_error=1;
                    DBG("Wrong MRU length field value\r\n");
                }else{
                    memcpy(&mru,opt->data,2);
                    mru=ntohs(mru);

                    if(mru>1492 || mru<576){
                        mru=htons(1492);
                        ixc_lcp_send(0xc021,IXC_LCP_CFG_NAK,id,2,&mru);
                        break;
                    }

                    ack_packet[ack_len]=opt->type;
                    ack_packet[ack_len+1]=opt->length+2;
                    memcpy(&ack_packet[ack_len+2],opt->data,opt->length);
                    ack_len=ack_len+opt->length+2;
                }
                break;
            case IXC_LCP_OPT_TYPE_AUTH_PROTO:
                    ack_packet[ack_len]=opt->type;
                    ack_packet[ack_len+1]=opt->length+2;
                    memcpy(&ack_packet[ack_len+2],opt->data,opt->length);
                    ack_len=ack_len+opt->length+2;
                if(opt->length<2){
                    is_error=1;
                    DBG("Wrong AUTH PROTO length field value\r\n");
                }else{
                    memcpy(&auth_proto,opt->data,2);
                    auth_proto=ntohs(auth_proto);
                    
                    if(auth_proto!=0xc023 && auth_proto!=0xc223){
                        auth_proto=htons(0xc223);
                        ixc_lcp_send(0xc021,IXC_LCP_CFG_NAK,id,2,&auth_proto);
                        break;
                    }

                    /**
                    if(auth_proto==0xc223 && opt->length!=3){

                        ack_packet[ack_len]=opt->type;
                        ack_packet[ack_len+1]=opt->length+2;
                        memcpy(&ack_packet[ack_len+2],opt->data,opt->length);
                        ack_len=ack_len+opt->length+2;
                        DBG("Wrong CHAP length field value\r\n");
                        break;
                    }**/
                }
                break;
            case IXC_LCP_OPT_TYPE_QUA_PROTO:
                tmp[0]=opt->type;
                tmp[1]=opt->length+2;

                memcpy(&tmp[2],opt->data,opt->length);
                ixc_lcp_send(0xc021,IXC_LCP_CFG_REJECT,id,opt->length+2,tmp);
                break;
            case IXC_LCP_OPT_TYPE_MAGIC_NUM:
                if(opt->length!=4){
                    is_error=1;
                    DBG("Wrong magic num length field value\r\n");
                }else{
                    ack_packet[ack_len]=opt->type;
                    ack_packet[ack_len+1]=opt->length+2;
                    memcpy(&ack_packet[ack_len+2],opt->data,4);

                    ack_len=ack_len+opt->length+2;
                }
                break;
            case IXC_LCP_OPT_TYPE_PROTO_COMP:
                tmp[0]=opt->type;
                tmp[1]=opt->length;

                memcpy(&tmp[2],opt->data,opt->length);
                ixc_lcp_send(0xc021,IXC_LCP_CFG_REJECT,id,opt->length+2,tmp);
                break;
            case IXC_LCP_OPT_TYPE_ADDR_CTL_COMP:
                tmp[0]=opt->type;
                tmp[1]=opt->length;

                memcpy(&tmp[2],opt->data,opt->length);
                ixc_lcp_send(0xc021,IXC_LCP_CFG_REJECT,id,opt->length+2,tmp);
                break;
            default:
                is_error=1;
                break;
        }
        opt=opt->next;
    }

    ixc_lcp_free_opts(first_opt);

    if(is_error) {
        STDERR("Server PPPOE protocol error\r\n");
        ixc_pppoe_reset();
    }else{
        ixc_lcp_send(0xc021,IXC_LCP_CFG_ACK,id,ack_len,ack_packet);
    }
}

static void ixc_lcp_handle_echo_req(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{
    ixc_lcp_send(0xc021,IXC_LCP_ECHO_REPLY,id,length,m->data+m->offset);
}

static void ixc_lcp_handle_echo_reply(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{

}

static void ixc_lcp_handle_cfg_ack(struct ixc_mbuf *m,unsigned char id,unsigned short length)
{
    struct ixc_lcp_opt *first_opt=NULL,*opt;
    int rs=ixc_lcp_parse_opts(m->data+m->offset,length,&first_opt);
    unsigned int magic_num=0;
    int is_err=0;
    int mru_neg_ok;

    if(rs<0){
        ixc_lcp_free_opts(first_opt);
        DBG("cannot parse lcp ack options\r\n");
        return;
    }

    opt=first_opt;
    

    while (NULL!=opt){
        switch(opt->type){
            case IXC_LCP_OPT_TYPE_MAGIC_NUM:
                memcpy(&magic_num,opt->data,opt->length);
                magic_num=ntohl(magic_num);
                if(lcp.magic_num!=magic_num) is_err=1;
                break;
            case IXC_LCP_OPT_TYPE_MAX_RECV_UNIT:
                mru_neg_ok=1;
                break;
            default:
                break;
        }
        opt=opt->next;
    }
    
    ixc_lcp_free_opts(first_opt);
    if(is_err) return;
    if(mru_neg_ok) lcp.mru_neg_ok=1;
}

int ixc_lcp_init(void)
{
    bzero(&lcp,sizeof(struct ixc_lcp));
    return 0;
}

void ixc_lcp_uninit(void)
{

}

void ixc_lcp_handle(struct ixc_mbuf *m)
{
    struct ixc_lcp_cfg_header *lcp_header=(struct ixc_lcp_cfg_header *)(m->data+m->offset);
    unsigned short length=ntohs(lcp_header->length);

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
            ixc_lcp_handle_cfg_request(m,lcp_header->id,length);
            break;
        case IXC_LCP_CFG_ACK:
            ixc_lcp_handle_cfg_ack(m,lcp_header->id,length);
            break;
        case IXC_LCP_CFG_NAK:
            break;
        case IXC_LCP_CFG_REJECT:
            break;
        case IXC_LCP_TERM_REQ:
            break;
        case IXC_LCP_TERM_ACK:
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
}

/// 协商请求发送
static void ixc_lcp_neg_send(unsigned char type,unsigned char length,void *data)
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
    unsigned short size;

    srand(time(NULL));
    rand_no=rand();
    lcp.magic_num=rand_no;
    rand_no=htonl(rand_no);

    data_set[0]=data;
    data_set[1]=(unsigned char *)(&rand_no);

    for(int n=0;n<2;n++){
        buf[size]=types[n];
        buf[size+1]=lengths[n]+2;

        memcpy(&buf[size+2],data_set[n],lengths[n]);

        size+=lengths[n]+2;
    }

    ixc_lcp_send(0xc021,IXC_LCP_CFG_REQ,1,size,buf);
}

static void ixc_lcp_neg_request_send_for_mru(void)
{
    unsigned short mru=htons(1492);
    ixc_lcp_neg_send(IXC_LCP_CFG_REQ,2,&mru);
}

void ixc_lcp_neg_request_send_auto(void)
{
    if(!lcp.mru_neg_ok){
        ixc_lcp_neg_request_send_for_mru();
        return;
    }
}

void ixc_lcp_loop(void)
{
    ixc_lcp_neg_request_send_auto();
}