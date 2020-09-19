#include<string.h>
#include<stdlib.h>
#include<arpa/inet.h>

#include "dhcp_client.h"
#include "dhcp.h"
#include "netif.h"
#include "ether.h"

#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

static struct ixc_dhcp_client dhcp_client;
static int dhcp_client_is_initialized=0;
static int dhcp_client_is_enabled=0;
static struct sysloop *dhcp_client_sysloop=NULL;

// 是否已经正常获取到IP地址
static int dhcp_client_get_ip_ok=0;

static int ixc_dhcp_client_opt_fill(unsigned char *buf,unsigned char code,unsigned char len,void *data,int is_finished)
{
    int v,r=0;

    buf[0]=code;
    buf[1]=len;

    r+=2;
    memcpy(buf+r,data,len);
    r+=len;

    /**v=len % 8;
    if(v){
        memset(buf+r,0,v);
        r+=v;
    }**/

    if(is_finished){
        memset(buf+r,0xff,1);
        r+=1;
    }

    return r;
}

static void ixc_dhcp_client_request_send(void)
{
    struct ixc_mbuf *m=ixc_mbuf_get();
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);

    struct ixc_dhcp *dhcp;
    struct netutil_iphdr *iphdr;
    struct netutil_udphdr *udphdr;
    struct ixc_dhcp_opt_msgtype *msgtype;

    unsigned char data[512];
    unsigned char *s_ptr;
    int size;
    unsigned int magic_cookie=0x63825363;
    unsigned short length;

    struct pseudo_header{
        unsigned char src_addr[4];
        unsigned char dst_addr[4];
        unsigned char __pad;
        unsigned char protocol;
        unsigned short length;
    } ps_hdr;

    unsigned short csum;

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return;
    }

    m->netif=netif;
    m->is_ipv6=0;
    m->link_proto=0x800;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->offset;
    m->tail=m->offset+sizeof(struct netutil_iphdr)+8+sizeof(struct ixc_dhcp);
    m->end=m->tail;

    memcpy(m->src_hwaddr,netif->hwaddr,6);
    memset(m->dst_hwaddr,0xff,6);

    iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    udphdr=(struct netutil_udphdr *)(m->data+m->offset+20);
    dhcp=(struct ixc_dhcp *)(m->data+m->offset+28);

    bzero(iphdr,20);
    bzero(udphdr,8);
    bzero(dhcp,236);

    srand(time(NULL));

    iphdr->ver_and_ihl=0x45;
    iphdr->tos=0x20;
    iphdr->id=(rand() & 0xffff);
    iphdr->frag_info=htons(0x4000);
    iphdr->ttl=64;
    iphdr->protocol=17;
    
    memset(iphdr->src_addr,0x00,4);
    memset(iphdr->dst_addr,0xff,4);

    udphdr->src_port=htons(68);
    udphdr->dst_port=htons(67);
    udphdr->length=htons(244);

    dhcp->op=1;
    dhcp->htype=1;
    dhcp->hlen=6;
    dhcp->hops=0;
    dhcp->xid=htonl(rand());
    dhcp->flags=0;

    memcpy(dhcp->chaddr,netif->hwaddr,6);
    s_ptr=m->data+m->tail;

    magic_cookie=htonl(magic_cookie);
    memcpy(s_ptr,&magic_cookie,4);
    s_ptr+=4;
    m->tail+=4;
    
    // 填充消息类型
    size=ixc_dhcp_client_opt_fill(s_ptr,53,1,"\1",0);
    m->tail+=size;
    s_ptr+=size;
    
    // 填充客户端ID
    size=ixc_dhcp_client_opt_fill(s_ptr,15,strlen(dhcp_client.hostname),dhcp_client.hostname,0);
    m->tail+=size;
    s_ptr+=size;

    // 填充客户端ID
    size=ixc_dhcp_client_opt_fill(s_ptr,61,6,netif->hwaddr,0);
    m->tail+=size;
    s_ptr+=size;

    // 填充vendor标识
    size=ixc_dhcp_client_opt_fill(s_ptr,43,strlen(dhcp_client.vendor),dhcp_client.vendor,0);
    m->tail+=size;
    s_ptr+=size;

    // 填充请求列表
    // 子网掩码
    data[0]=1; 
    // 路由器地址
    data[1]= 3;
    // 域名
    data[2]=15;
    size=ixc_dhcp_client_opt_fill(s_ptr,55,3,data,1);
    m->tail+=size;
    s_ptr+=size;

    m->end=m->tail;


    // 计算UDP检验和
    memcpy(ps_hdr.src_addr,iphdr->src_addr,4);
    memcpy(ps_hdr.dst_addr,iphdr->dst_addr,4);

    length=m->tail-m->offset-20;
    udphdr->length=htons(length);

    ps_hdr.__pad=0;
    ps_hdr.protocol=17;
    ps_hdr.length=udphdr->length;

    memcpy(data,&ps_hdr,12);
    memcpy(data+12,udphdr,length);

    csum=csum_calc((unsigned short *)data,length);
    udphdr->checksum=csum;

    // 计算IP头部检验和
    iphdr->tot_len=htons(m->tail-m->offset);
    csum=csum_calc((unsigned short *)iphdr,20);
    iphdr->checksum=csum;

    ixc_ether_send(m,1);

    STDERR("hello,dhcp request\r\n");
}

static void ixc_dhcp_client_sysloop_cb(struct sysloop *lp)
{
    time_t now_time=time(NULL);

    if(now_time-dhcp_client.up_time < 10) return;

    ixc_dhcp_client_request_send();
}

int ixc_dhcp_client_init(void)
{
    bzero(&dhcp_client,sizeof(struct ixc_dhcp_client));

    dhcp_client_is_initialized=1;
    dhcp_client.up_time=time(NULL);

    strcpy(dhcp_client.hostname,"ixcsys");
    strcpy(dhcp_client.vendor,"ixcsys");

    return 0;
}

void ixc_dhcp_client_uninit(void)
{
    dhcp_client_is_initialized=0;
}

int ixc_dhcp_client_enable(int enable)
{
    if(!dhcp_client_is_initialized){
        STDERR("dhcp client not initialized\r\n");
        return -1;
    }

    dhcp_client_is_enabled=enable;

    if(!enable){
        if(NULL!=dhcp_client_sysloop) sysloop_del(dhcp_client_sysloop);
        return 0;
    }

    dhcp_client_sysloop=sysloop_add(ixc_dhcp_client_sysloop_cb,NULL);
    if(NULL==dhcp_client_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    return 0;
}

inline
int ixc_dhcp_client_is_enabled(void)
{
    return dhcp_client_is_enabled;
}

void ixc_dhcp_client_handle(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}