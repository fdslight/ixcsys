#include<string.h>
#include<arpa/inet.h>

#include "pppoe.h"
#include "ether.h"
#include "netif.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/sysloop.h"

static int pppoe_is_initialized=0;
static struct ixc_pppoe pppoe;
static struct sysloop *pppoe_sysloop=NULL;

static void ixc_pppoe_sysloop_cb(struct sysloop *lp)
{

}

/// 构建PPPoE tag

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

///  设置PPPOE的用户名和密码
int ixc_pppoe_set_user(char *username,char *passwd)
{
    strcpy(pppoe.username,username);
    strcpy(pppoe.passwd,passwd);

    return 0;
}

/// 开始进行PPPoE的会话
void ixc_pppoe_start(void)
{
    pppoe.is_started=1;
    // 发送PPPoE的会话报文

}

/// 把数据包发送PPPOE进行处理
void ixc_pppoe_handle(struct ixc_mbuf *m)
{
    // 未开启PPPoE直接发送数据
    if(!pppoe.enable){
        ixc_ether_send(m,1);
        return;
    }
    
    ixc_mbuf_put(m);
}

int ixc_pppoe_ok(void)
{
    return pppoe.pppoe_ok;
}

int ixc_pppoe_enable(int status)
{
    pppoe.enable=status;

    return 0;
}

inline
int ixc_pppoe_is_enabled(void)
{
    return pppoe.enable;
}