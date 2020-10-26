#include<string.h>
#include<arpa/inet.h>

#include "pppoe.h"
#include "ether.h"
#include "netif.h"
#include "debug.h"
#include "router.h"

#include "../../../pywind/clib/sysloop.h"

static int pppoe_is_initialized=0;
static struct ixc_pppoe pppoe;
static struct sysloop *pppoe_sysloop=NULL;

static void ixc_pppoe_send_discovery(void);
static void ixc_pppoe_send_discovery_padr(void);

/// PPPoE标签解析
static int ixc_pppoe_parse_tags(struct ixc_mbuf *m,struct ixc_pppoe_tag **tag_first)
{
    struct ixc_pppoe_tag *first=NULL,*cur,*tmp;
    struct ixc_pppoe_tag_header *tag_header;
    int tot_size=m->tail-m->offset-6;
    int rs=0,pos=0,t;
    unsigned short length,type;

    *tag_first=NULL;
    first=NULL;
    cur=NULL;

    while(1){
        if(pos==tot_size) break;

        tag_header=(struct ixc_pppoe_tag_header *)(m->data+m->offset+6+pos);
        length=ntohs(tag_header->length);
        type=ntohs(tag_header->type);

        t=pos+4+length;

        // 这里的4代表tag的头部长度
        if(t>tot_size){
            DBG("Wrong tag length %d %d\r\n",pos+length+4,tot_size);
            rs=-1;
            break;
        }

        if(type==0x0000) break;

        // 检查tag长度值是否合法
        if(length>1492){
            DBG("Wrong tag length value\r\n");
            rs=-1;
            break;
        }

        tmp=malloc(sizeof(struct ixc_pppoe_tag));

        if(NULL==tmp){
            rs=-1;
            STDERR("cannot malloc struct ixc_pppoe_tag\r\n");
            break;
        }

        tmp->next=NULL;
        tmp->type=type;
        tmp->length=length;

        memcpy(tmp->data,m->data+m->offset+6+pos+4,length);

        if(NULL==first){
            first=tmp;
            cur=tmp;
        }else{
            cur->next=tmp;
            cur=tmp;
        }
        pos=t;
    }

    *tag_first=first;

    return rs;
}

/// 释放标签内存
static void ixc_pppoe_free_tags(struct ixc_pppoe_tag *tag_first)
{
    struct ixc_pppoe_tag *tag=tag_first,*tmp;

    while(NULL!=tag){
        tmp=tag->next;
        free(tag);
        tag=tmp;
    }
}

static void ixc_pppoe_discovery_loop(void)
{
    // 如果发现阶段还是0,那么发送发现数据包
    if(pppoe.cur_discovery_stage==0){
        ixc_pppoe_send_discovery();
        return;
    }
    
    // 如果当前是PADR阶段,那么发送PADR数据包
    if(pppoe.cur_discovery_stage==IXC_PPPOE_CODE_PADR){
        ixc_pppoe_send_discovery_padr();
        return;
    }
}

static void ixc_pppoe_sysloop_cb(struct sysloop *lp)
{
    time_t now=time(NULL);
    // 检查最近更新时间
    if(now-pppoe.up_time<10 && !pppoe.discovery_ok) return;

    // 大于60s那么重置
    if(now-pppoe.up_time>60){
        ixc_pppoe_reset();
        return;
    }

    if(!pppoe.discovery_ok) ixc_pppoe_discovery_loop();
}

/// 发送PPPoE发现报文
static void ixc_pppoe_send_discovery(void)
{
    struct ixc_mbuf *m=ixc_mbuf_get();
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    struct ixc_pppoe_header *header;
    struct ixc_pppoe_tag_header *tag_header;

    unsigned char brd[]={
        0xff,0xff,0xff,
        0xff,0xff,0xff
    };

    if(NULL==netif){
        STDERR("cannot get netif for WAN\r\n");
        return;
    }

    if(NULL==m){
        STDERR("cannot get mbuf for PPPoE\r\n");
        return;
    }

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,brd,6);

    m->netif=netif;
    m->link_proto=0x8863;

    m->begin=IXC_MBUF_BEGIN;
    m->offset=IXC_MBUF_BEGIN;

    header=(struct ixc_pppoe_header *)(m->data+m->offset);

    header->ver_and_type=0x11;
    header->code=IXC_PPPOE_CODE_PADI;
    header->session_id=0x0000;
    header->length=htons(4);

    tag_header=(struct ixc_pppoe_tag_header *)(((char *)header)+6);
    tag_header->type=htons(0x0101);
    tag_header->length=0;

    m->tail=m->begin+10;
    m->end=m->tail;

    pppoe.up_time=time(NULL);

    ixc_ether_send(m,1);
}

int ixc_pppoe_init(void)
{
    bzero(&pppoe,sizeof(struct ixc_pppoe));


    pppoe_sysloop=sysloop_add(ixc_pppoe_sysloop_cb,NULL);
    if(NULL==pppoe_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    pppoe_is_initialized=1;

    return 0;
}

void ixc_pppoe_uninit(void)
{
    pppoe_is_initialized=0;
}

/// 开始进行PPPoE的会话
void ixc_pppoe_start(void)
{
    if(!pppoe_is_initialized){
        STDERR("the pppoe is not initialized\r\n");
        return;
    }

    pppoe.is_started=1;
    // 发送PPPoE的会话报文
    pppoe.up_time=time(NULL);
}

/// 
void ixc_pppoe_stop(void)
{
    // 如果PPPoE会话成功那么发送终止信号终止PPPoE会话
}

/// 发送PADR数据包
static void ixc_pppoe_send_discovery_padr(void)
{
    struct ixc_pppoe_header *header;
    struct ixc_pppoe_tag_header *tag_header;

    unsigned short tot_size=6;

    unsigned short tags[]={
        0x0101,
        0x0102,0x0104,0x0000
    },tag;
    unsigned short lengths[]={
        0,
        strlen(pppoe.ac_name),pppoe.ac_cookie_len,0
    },length;
    unsigned char *data_set[]={
        NULL,
        (unsigned char *)pppoe.ac_name,pppoe.ac_cookie,NULL
    },*data;

    struct ixc_mbuf *m=ixc_mbuf_get();

    pppoe.up_time=time(NULL);

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return;
    }

    m->netif=ixc_netif_get(IXC_NETIF_WAN);
    m->next=NULL;
    m->from=IXC_MBUF_FROM_WAN;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->begin;
    m->link_proto=0x8863;

    header=(struct ixc_pppoe_header *)(m->data+m->offset);
    header->ver_and_type=0x11;
    header->code=IXC_PPPOE_CODE_PADR;
    header->session_id=0x0000;
    
    for(int n=0;;n++){
        tag_header=(struct ixc_pppoe_tag_header *)(m->data+m->offset+tot_size);

        tag=tags[n];
        length=lengths[n];
        data=data_set[n];
 
        tag_header->type=htons(tag);
        tag_header->length=htons(length);

        memcpy(m->data+m->offset+tot_size+4,data,length);

        tot_size=tot_size+length+4;
        if(tag==0x0000) break;
    }

    // 需要减去PPPoE头部的6个字节
    header->length=htons(tot_size-6);

    m->tail=m->offset+tot_size;
    m->end=m->tail;

    memcpy(m->src_hwaddr,m->netif->hwaddr,6);
    memcpy(m->dst_hwaddr,pppoe.selected_server_hwaddr,6);

    ixc_ether_send(m,1);
}

static void ixc_pppoe_handle_discovery_response(struct ixc_mbuf *m,struct ixc_pppoe_header *header)
{
    struct ixc_pppoe_tag *first_tag=NULL,*tmp_tag;
    int rs=ixc_pppoe_parse_tags(m,&first_tag);
    int have_ac_name=0;
    int error=0;
    char err_msg[2048];
    
    err_msg[0]='\0';

    if(rs<0){
        ixc_mbuf_put(m);
        ixc_pppoe_free_tags(first_tag);

        DBG("Wrong PPPoE tag format\r\n");
        return;
    }

    tmp_tag=first_tag;
    while(NULL!=tmp_tag){
        switch(tmp_tag->type){
            case 0x0102:
                if(header->code==IXC_PPPOE_CODE_PADO){
                    have_ac_name=1;
                    memcpy(pppoe.ac_name,tmp_tag->data,tmp_tag->length);
                    pppoe.ac_name[tmp_tag->length]='\0';
                }
                break;
            case 0x0104:
                if(header->code==IXC_PPPOE_CODE_PADO){
                    memcpy(pppoe.ac_cookie,tmp_tag->data,tmp_tag->length);
                    pppoe.ac_cookie_len=tmp_tag->length;
                }
                break;
            case 0x0201:
            case 0x0202:
            case 0x0203:
                error=tmp_tag->type;
                memcpy(err_msg,tmp_tag->data,tmp_tag->length);
                err_msg[tmp_tag->length]='\0';
                break;
        }

        tmp_tag=tmp_tag->next;
    }

    ixc_pppoe_free_tags(first_tag);
    ixc_mbuf_put(m);

    // 必须包含ac_name
    if(!have_ac_name && header->code==IXC_PPPOE_CODE_PADO) return;

    if(error || header->code==IXC_PPPOE_CODE_PADT){
        ixc_router_tell("lcp_stop");
        ixc_pppoe_reset();
        STDERR("errcode:0x%x %s\r\n",error,err_msg);
        return;
    }

    if(header->code==IXC_PPPOE_CODE_PADO){
        pppoe.cur_discovery_stage=IXC_PPPOE_CODE_PADR;
        // 发送PPPoE PADR数据包
        ixc_pppoe_send_discovery_padr();
        return;
    }

    if(header->code==IXC_PPPOE_CODE_PADS){
        pppoe.discovery_ok=1;
        pppoe.session_id=ntohs(header->session_id);
        ixc_router_tell("lcp_start");
        return;
    }
}

static void ixc_pppoe_handle_discovery(struct ixc_mbuf *m)
{
    struct ixc_pppoe_header *header=(struct ixc_pppoe_header *)(m->data+m->offset);

    // 检查服务器的响应代码是否符合要求
    if(header->code!=IXC_PPPOE_CODE_PADO && header->code!=IXC_PPPOE_CODE_PADS && header->code!=IXC_PPPOE_CODE_PADT){
        ixc_mbuf_put(m);
        return;
    }

    // 处理PADO报文
    if(header->code==IXC_PPPOE_CODE_PADO){
        pppoe.is_selected_server=1;

        memcpy(pppoe.selected_server_hwaddr,m->src_hwaddr,6);
        ixc_pppoe_handle_discovery_response(m,header);
        return;
    }

    // 检查是否是选择的PPPoE服务器
    if(memcmp(pppoe.selected_server_hwaddr,m->src_hwaddr,6)){
        ixc_mbuf_put(m);
        return;
    }

    if(header->code==IXC_PPPOE_CODE_PADS){
        ixc_pppoe_handle_discovery_response(m,header);
        return;
    }

    if(header->code==IXC_PPPOE_CODE_PADT){
        // 此处检查session是否一致
        if(ntohs(header->session_id)!=pppoe.session_id){
            ixc_mbuf_put(m);
            return;
        }
        ixc_pppoe_handle_discovery_response(m,header);
        return;
    }

    ixc_mbuf_put(m);
}

static void ixc_pppoe_handle_session(struct ixc_mbuf *m)
{
    struct ixc_pppoe_header *pppoe_header=(struct ixc_pppoe_header *)(m->data+m->offset);
    unsigned short ppp_proto=0,length;

    // 会话阶段code必须为0
    if(pppoe_header->code!=0){
        DBG("code must be zero at session\r\n");
        ixc_mbuf_put(m);
        return;
    }

    if(ntohs(pppoe_header->session_id)!=pppoe.session_id){
        DBG("wrong pppoe session ID\r\n");
        ixc_mbuf_put(m);
        return;
    }

    memcpy(&ppp_proto,m->data+m->offset+6,2);
    ppp_proto=ntohs(ppp_proto);
    length=htons(pppoe_header->length);
    
    // 此处增加偏移量
    m->offset+=8;

    switch(ppp_proto){
        // LCP
        case 0xc021:
        // PAP
        case 0xc023:
        // CHAP协议
        case 0xc223:
        // IPCP
        case 0x8021:
        // IPv6CP
        case 0x8057:
            ixc_router_pppoe_session_send(ppp_proto,length-2,m->data+m->offset);
            break;
        // IPv6协议
        case 0x0057:
            break;
        // IP协议
        case 0x0021:
            break;
        default:
            DBG("unkown PPPoE protocol 0x%x\r\n",ppp_proto);
            break;
    }
    ixc_mbuf_put(m);
}

/// 把数据包发送PPPOE进行处理
void ixc_pppoe_handle(struct ixc_mbuf *m)
{
    struct ixc_pppoe_header *header=(struct ixc_pppoe_header *)(m->data+m->offset);
    unsigned short length=ntohs(header->length);

    // PPPoE未开启那么直接丢弃数据
    if(!pppoe.enable){
        ixc_mbuf_put(m);
        return;
    }

    if(m->tail-m->offset<8){
        ixc_mbuf_put(m);
        DBG("wrong pppoe data packet\r\n");
        return;
    }

    if(header->ver_and_type!=0x11){
        ixc_mbuf_put(m);
        DBG("Wrong PPPoE version and type\r\n");
        return;
    }

    if(length<2){
        DBG("wrong pppoe payload length\r\n");
        ixc_mbuf_put(m);
        return;
    }

    // 这里不是等于号的理由是以太网会填充字段
    if(length > m->tail-m->offset){
        DBG("Wrong PPPoE length\r\n");
        ixc_mbuf_put(m);
        return;
    }

    // 屏蔽以太网的填充字段
    m->tail=m->offset+length+6;

    // 如果PPPoE第一阶段没成功那么丢弃session数据包
    if(m->link_proto==0x8864 && !pppoe.discovery_ok){
        ixc_mbuf_put(m);
        return;
    }

    if(m->link_proto==0x8863) ixc_pppoe_handle_discovery(m);
    else ixc_pppoe_handle_session(m);

}

void ixc_pppoe_set_ok(int ok)
{
    pppoe.pppoe_ok=ok;
}

int ixc_pppoe_enable(int status)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    pppoe.enable=status;

    // 设置MTU的值为1492
    netif->mtu_v4=1492;
    netif->mtu_v6=1492;
    
    return 0;
}

inline
int ixc_pppoe_is_enabled(void)
{
    return pppoe.enable;
}

void ixc_pppoe_send(struct ixc_mbuf *m)
{
    struct ixc_pppoe_header *header;
    unsigned short *proto_ptr;

    // 没有开启PPPoE那么丢弃数据包
    if(!pppoe.enable){
        ixc_mbuf_put(m);
        return;
    }
    // PPPoE没握手完成那么丢弃数据包
    if(!pppoe.pppoe_ok){
        ixc_mbuf_put(m);
        return;
    }

    // 此处检查链路层协议是否合法
    // 限制PPPoE协议只支持IP协议和IPv6协议
    if(m->link_proto!=0x0800 && m->link_proto!=0x86dd){
        ixc_mbuf_put(m);
        return;
    }

    // 对IP和IPv6数据包进行PPPoE封装
    header=(struct ixc_pppoe_header *)(m->data+m->begin-8);
    header->ver_and_type=0x11;
    header->code=0x00;
    header->session_id=htons(pppoe.session_id);
    
    // 这里需要加上PPP上的协议的两个字节
    header->length=htons(m->end-m->begin+2);

    proto_ptr=(unsigned short *)(m->data+m->offset-6);

    if(m->link_proto==0x0800) *proto_ptr=htons(0x0021);
    else *proto_ptr=htons(0x0057);

    m->begin=m->begin-8;
    m->offset=m->begin;
    
    m->link_proto=0x8864;

    // 修改目标MAC地址为PPPoE服务器的地址
    memcpy(m->dst_hwaddr,pppoe.selected_server_hwaddr,6);

    ixc_ether_send(m,1);
}

/// 发送PPPoE会话数据包
void ixc_pppoe_send_session_packet(unsigned short ppp_protocol,unsigned short length,void *data)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    struct ixc_mbuf *m=NULL;
    struct ixc_pppoe_header *pppoe_header=NULL;
    unsigned short *protocol;

    int is_permit=0;

    // 设置允许的协议范围
    switch(ppp_protocol){
        //LCP
        case 0xc021:
        // PAP
        case 0xc023:
        // CHAP
        case 0xc223:
        // IPCP
        case 0x8021:
        // IPv6CP
        case 0x8057:
            is_permit=1;
            break;
        default:
            break;
    }

    // 不允许的协议直接丢弃数据包
    if(!is_permit) return;

    m=ixc_mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return;
    }

    m->next=NULL;
    m->netif=netif;
    m->from=IXC_MBUF_FROM_WAN;
    m->link_proto=0x8864;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=m->offset+6+4+length;
    m->end=m->tail;

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memcpy(m->dst_hwaddr,pppoe.selected_server_hwaddr,6);

    pppoe_header=(struct ixc_pppoe_header *)(m->data+m->offset);
    pppoe_header->ver_and_type=0x11;
    pppoe_header->code=0x00;
    pppoe_header->session_id=htons(pppoe.session_id);
    // 这里需要加上PPP上的协议的两个字节
    pppoe_header->length=htons(length+2);

    protocol=(unsigned short *)(m->data+m->offset+6);
    *protocol=htons(ppp_protocol);

    memcpy(m->data+m->offset+8,data,length);

    //DBG("session send\r\n");

    ixc_ether_send(m,1);
}

/// 重置会话
void ixc_pppoe_reset()
{
    // 这里需要更新时间,否则会导致超时不发送请求包
    pppoe.up_time=time(NULL);
    pppoe.discovery_ok=0;
    pppoe.is_selected_server=0;
    pppoe.cur_discovery_stage=0;
    pppoe.pppoe_ok=0;
}

inline
struct ixc_pppoe *ixc_pppoe(void)
{
    return &pppoe;
}
