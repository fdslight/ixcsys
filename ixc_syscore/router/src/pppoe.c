#include<string.h>
#include<arpa/inet.h>

#include "pppoe.h"
#include "ether.h"
#include "netif.h"
#include "debug.h"
#include "router.h"
#include "ip.h"
#include "ip6.h"
#include "route.h"

#include "../../../pywind/clib/sysloop.h"

static int pppoe_is_initialized=0;
static struct ixc_pppoe pppoe;
static struct sysloop *pppoe_sysloop=NULL;

static void ixc_pppoe_send_discovery(void);
static void ixc_pppoe_send_discovery_padr(void);
static void ixc_pppoe_send_padt(void);

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
        if(length>256){
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
    /*if(pppoe.cur_discovery_stage==IXC_PPPOE_CODE_PADR){
        ixc_pppoe_send_discovery_padr();
        return;
    }*/
}

static void ixc_pppoe_sysloop_cb(struct sysloop *lp)
{
    time_t now=time(NULL);
    if(!pppoe.enable) return;
    // 检查最近更新时间
    if(now-pppoe.up_time<10 && !pppoe.discovery_ok) return;

    // 大于60s pppoe未找到协商服务器,那么重置
    if(now-pppoe.up_time>60 && !pppoe.pppoe_ok){
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
    int offset;
    char *ptr;

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
    ptr=(char *)(m->data+m->offset);

    header->ver_and_type=0x11;
    header->code=IXC_PPPOE_CODE_PADI;
    header->session_id=0x0000;
    

    offset=6;
    
    // pppoe service name
    tag_header=(struct ixc_pppoe_tag_header *)(ptr+offset);
    tag_header->type=htons(0x0101);
    tag_header->length=htons(strlen(pppoe.service_name));

    offset+=4;

    strcpy(ptr+offset,pppoe.service_name);
    offset+=strlen(pppoe.service_name);

    // pppoe host uniq
    if(pppoe.host_uniq_length>0){
        tag_header=(struct ixc_pppoe_tag_header *)(ptr+offset);
        tag_header->type=htons(0x0103);
        tag_header->length=htons(pppoe.host_uniq_length);

        offset+=4;
        memcpy(ptr+offset,pppoe.host_uniq,pppoe.host_uniq_length);
        
        offset+=pppoe.host_uniq_length;
    }
    
    tag_header=(struct ixc_pppoe_tag_header *)(ptr+offset);
    tag_header->type=htons(0x0000);
    tag_header->length=0;

    offset+=4;

    // 除去头部的大小
    header->length=htons(offset-6);

    m->tail=m->begin+offset;
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

    bzero(&pppoe,sizeof(struct ixc_pppoe));
    
    //pppoe.is_forced_ac_name=1;
    //strcpy(pppoe.force_ac_name,"ZJLSH-MC-CMNET-BRAS01-TN_ME60-X8");

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
    
    char content[4096];

    unsigned short tot_size=6;

    unsigned short tags[]={
        0x0101,
        0x0102,
        0x0103,
        0x0104,
        0x0000
    },tag;
    unsigned short lengths[]={
        strlen(pppoe.service_name),
        strlen(pppoe.ac_name),
        pppoe.host_uniq_length,
        pppoe.ac_cookie_len,
        0
    },length;
    unsigned char *data_set[]={
        (unsigned char *)pppoe.service_name,
        (unsigned char *)pppoe.ac_name,
        pppoe.host_uniq,
        pppoe.ac_cookie,
        NULL
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
        
        // 未设置host uniq跳过
        if(0==length && 0x0103==tag) continue;
        // 未设置ac cookie跳过
        if(0==length && 0x0104==tag) continue;
        
        
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

    // 告知选择的ac设备
    strcpy(content,"pppoe_selected_ac_name ");
    strcat(content,pppoe.ac_name);
    ixc_router_tell(content);

    //DBG_FLAGS;

    ixc_ether_send(m,1);
}

static void ixc_pppoe_send_padt(void)
{
    struct ixc_pppoe_header *header;
    struct ixc_mbuf *m=ixc_mbuf_get();

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
    header->code=IXC_PPPOE_CODE_PADT;
    header->session_id=htons(pppoe.session_id);
    header->length=0;

    m->tail=m->end=m->begin+6;

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
    // 是否是同一个AC,有时候会返回多个AC
    int is_same_ac=1;
    char err_msg[2048];
    char ac_name[2048];
    char content[4096];
    
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
                have_ac_name=1;

                memcpy(ac_name,tmp_tag->data,tmp_tag->length);
                ac_name[tmp_tag->length]='\0';

                if(header->code==IXC_PPPOE_CODE_PADO){
                    if(!pppoe.is_selected_server){
                        memcpy(pppoe.ac_name,tmp_tag->data,tmp_tag->length);
                        pppoe.ac_name[tmp_tag->length]='\0';
                    }else{
                        if(memcmp(pppoe.ac_name,tmp_tag->data,tmp_tag->length)){
                            is_same_ac=0;
                        }
                    }
                }
                break;
            case 0x0104:
                if(header->code==IXC_PPPOE_CODE_PADO){
                    if(!pppoe.is_selected_server){
                        memcpy(pppoe.ac_cookie,tmp_tag->data,tmp_tag->length);
                        pppoe.ac_cookie_len=tmp_tag->length;
                    }
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
    
    // PADT不带任何标签,因此逻辑要放在最前面
    if(error || header->code==IXC_PPPOE_CODE_PADT){
        ixc_router_tell("lcp_stop");
        ixc_pppoe_reset();
        ixc_mbuf_put(m);
        //STDERR("errcode:0x%x %s\r\n",error,err_msg);
        DBG("PPPoE server terminate session,errcode 0x%x,error message is %s\r\n",error,err_msg);
        return;
    }

    // 必须包含ac_name
    if(!have_ac_name) {
        ixc_mbuf_put(m);
        DBG_FLAGS;
        return;
    }
    
    // 告知AC name
    strcpy(content,"pppoe_ac_name ");
    strcat(content,ac_name);
    ixc_router_tell(content);

    if(!is_same_ac){
        ixc_mbuf_put(m);
        DBG("PPPoE receive new AC %s,system ignore it\r\n",ac_name);
        return;
    }

    if(pppoe.is_forced_ac_name && strcmp(pppoe.force_ac_name,ac_name)!=0){
        ixc_mbuf_put(m);
        DBG("PPPoE force ac name %s,but current ac name is %s\r\n",pppoe.force_ac_name,ac_name);
        return;
    }

    // 如果选择了服务器,检查硬件地址,可能存在多个相同ac不同硬件地址的情况
    if(pppoe.is_selected_server && memcmp(pppoe.selected_server_hwaddr,m->src_hwaddr,6)){
        ixc_mbuf_put(m);
        return;
    }

    if(header->code==IXC_PPPOE_CODE_PADO){
        pppoe.is_selected_server=1;
        pppoe.cur_discovery_stage=IXC_PPPOE_CODE_PADR;
        // 发送PPPoE PADR数据包
        ixc_pppoe_send_discovery_padr();
        ixc_mbuf_put(m);
        return;
    }

    if(header->code==IXC_PPPOE_CODE_PADS){
        pppoe.cur_discovery_stage=IXC_PPPOE_CODE_PADS;
        pppoe.discovery_ok=1;
        pppoe.session_id=ntohs(header->session_id);
        ixc_mbuf_put(m);
        ixc_router_tell("lcp_start");
        return;
    }
    ixc_mbuf_put(m);
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
        // 检查是否是同一台PPPoE服务器
        if(!pppoe.is_selected_server || memcmp(pppoe.selected_server_hwaddr,m->src_hwaddr,6)){
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

    if(!pppoe.discovery_ok){
        DBG("pppoe not discovery ok,drop session packet\r\n");
        ixc_mbuf_put(m);
        return;
    }

    // 会话阶段code必须为0
    if(pppoe_header->code!=0){
        DBG("code must be zero at session\r\n");
        ixc_mbuf_put(m);
        return;
    }

    if(ntohs(pppoe_header->session_id)!=pppoe.session_id){
        DBG("wrong pppoe session ID,local is 0x%x,server is 0x%x\r\n",pppoe.session_id,ntohs(pppoe_header->session_id));
        ixc_mbuf_put(m);
        return;
    }

    // 检查mac地址是否是选中的PPPoE Server
    if(memcmp(pppoe.selected_server_hwaddr,m->src_hwaddr,6)){
        ixc_mbuf_put(m);
        return;
    }

    memcpy(&ppp_proto,m->data+m->offset+6,2);
    ppp_proto=ntohs(ppp_proto);
    length=ntohs(pppoe_header->length);
    
    // 此处增加偏移量和屏蔽pppoe头部
    m->offset+=8;
    m->begin=m->offset;

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
            ixc_mbuf_put(m);
            break;
        // IPv6协议
        case 0x0057:
            ixc_ip6_handle(m);
            break;
        // IP协议
        case 0x0021:
            ixc_ip_handle(m);
            break;
        default:
            ixc_mbuf_put(m);
            DBG("unkown PPPoE protocol 0x%x\r\n",ppp_proto);
            break;
    }
}

/// 把数据包发送PPPOE进行处理
void ixc_pppoe_handle(struct ixc_mbuf *m)
{
    struct ixc_pppoe_header *header=(struct ixc_pppoe_header *)(m->data+m->offset);
    unsigned short length=ntohs(header->length);

    // PPPoE未开启那么直接丢弃数据
    if(!pppoe.enable){
        DBG("pppoe not enable,drop data packet\r\n");
        ixc_mbuf_put(m);
        return;
    }

    if(IXC_MBUF_FROM_LAN==m->from){
        //DBG_FLAGS;
        ixc_pppoe_send(m);
        return;
    }

    if(m->tail-m->offset<8){
        ixc_mbuf_put(m);
        DBG("wrong pppoe data packet\r\n");
        return;
    }

    if(header->ver_and_type!=0x11){
        ixc_mbuf_put(m);
        DBG("Wrong PPPoE version and type,wrong value is %d\r\n",header->ver_and_type);
        return;
    }
    
    if(length>1500){
        DBG("wrong pppoe payload length,wrong length is %d\r\n",length);
        ixc_mbuf_put(m);
        return;
    }

    // 这里不是等于号的理由是以太网会填充字段
    /*if(length > m->tail-m->offset){
        DBG("Wrong PPPoE length\r\n");
        ixc_mbuf_put(m);
        return;
    }*/

    // 屏蔽以太网的填充字段
    m->end=m->tail=m->offset+length+6;

    // 如果PPPoE第一阶段没成功那么丢弃session数据包
    if(m->link_proto==0x8864 && !pppoe.discovery_ok){
        //DBG_FLAGS;
        ixc_mbuf_put(m);
        return;
    }
    //DBG_FLAGS;
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

    if(status){
        // 设置MTU的值为1492
        netif->mtu_v4=1492;
        netif->mtu_v6=1492;
    }else{
        // 恢复默认mtu
        netif->mtu_v4=1500;
        netif->mtu_v6=1500;
    }

    if(status){
        // 关闭直通,某些程序可能会在pppoe开启之前通过普通ipv6_pass_enable开启直通,这里强制关闭
        ixc_route_ipv6_pass_force_enable(0);
    }

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
        DBG("PPPoE not enable,cannot send packet to PPPoE server\r\n");
        ixc_mbuf_put(m);
        return;
    }
    // PPPoE没握手完成那么丢弃数据包
    if(!pppoe.pppoe_ok){
        DBG("PPPoE not ready OK,cannot send packet to PPPoE server\r\n");
        ixc_mbuf_put(m);
        return;
    }

    // 此处检查链路层协议是否合法
    // 限制PPPoE协议只支持IP协议和IPv6协议
    if(m->link_proto!=0x0800 && m->link_proto!=0x86dd){
        DBG("PPPoE not support link layer protocol 0x%x\r\n",m->link_proto);
        ixc_mbuf_put(m);
        return;
    }

    // 对IP和IPv6数据包进行PPPoE封装
    m->offset=m->offset-8;
    header=(struct ixc_pppoe_header *)(m->data+m->offset);
    header->ver_and_type=0x11;
    header->code=0x00;
    header->session_id=htons(pppoe.session_id);
    
    // 计算PPPoE payload长度
    header->length=htons(m->end-m->offset-6);

    proto_ptr=(unsigned short *)(m->data+m->offset+6);

    if(m->link_proto==0x0800) *proto_ptr=htons(0x0021);
    else *proto_ptr=htons(0x0057);

    m->begin=m->offset;
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
    // 如果此处发现成功,那么发送PPPoE终止报文
    if(pppoe.discovery_ok){
        ixc_pppoe_send_padt();
    }

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


int ixc_pppoe_force_ac_name(const char *name,int is_forced)
{
    pppoe.is_forced_ac_name=is_forced;

    if(is_forced){
        strcpy(pppoe.force_ac_name,name);
        return 0;
    }

    pppoe.force_ac_name[0]='\0';

    return 0;
}

/// 设置host_uniq
int ixc_pppoe_set_host_uniq(const char *uniq,size_t length)
{

    //DBG("host uniq length %lu\r\n",length);

    pppoe.host_uniq_length=length;

    if(length>2048){
        return -1;
    }

    memcpy(pppoe.host_uniq,uniq,length);

    return 0;
}

/// 设置服务名
int ixc_pppoe_set_service_name(const char *service_name)
{
    if(NULL==service_name){
        pppoe.service_name[0]='\0';
        return 0;
    }

    // 检查字符串长度
    if(strlen(service_name)>2047){
        pppoe.service_name[0]='\0';
        return -1;
    }

    //DBG("service name is %s\r\n",service_name);
    strcpy(pppoe.service_name,service_name);

    return 0;
}