#include <string.h>
#include <arpa/inet.h>

#include "qos.h"
#include "nat.h"
#include "route.h"
#include "addr_map.h"
#include "debug.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static struct ixc_qos ixc_qos;
static int ixc_qos_is_initialized = 0;
static struct sysloop *qos_sysloop=NULL;
/// 包数目
static unsigned long long qos_pkt_num=0;

static void ixc_qos_sysloop_cb(struct sysloop *lp)
{
    // 弹出数据包
    ixc_qos_pop();
}

inline static int ixc_qos_calc_slot(unsigned char a, unsigned char b, unsigned char c,unsigned char d)
{
    unsigned int v= (a << 24) | (b<<16) | (c<<8) | d;
    int slot_num= v % IXC_QOS_SLOT_NUM;

    return slot_num;
}

static void ixc_qos_put(struct ixc_mbuf *m,unsigned char a,unsigned char b,unsigned char c,unsigned char d)
{
    int slot_no;
    struct ixc_qos_slot *slot_obj;

    m->next=NULL;
    slot_no=ixc_qos_calc_slot(a,b,c,d);
    slot_obj=ixc_qos.slot_objs[slot_no];

    // 包的数目增加1
    qos_pkt_num+=1;

    if(!slot_obj->is_used){
        slot_obj->is_used=1;
        slot_obj->mbuf_first=m;
        slot_obj->mbuf_last=m;

        slot_obj->next=ixc_qos.slot_head;
        ixc_qos.slot_head=slot_obj;
        return;
    }

    slot_obj->mbuf_last->next=m;
    slot_obj->mbuf_last=m;
}

static void ixc_qos_send_to_next(struct ixc_mbuf *m)
{
    qos_pkt_num-=1;

    if(IXC_MBUF_FROM_LAN==m->from){
        //DBG_FLAGS;
        if(m->is_ipv6) ixc_addr_map_handle(m);
        else ixc_nat_handle(m);
    }else{
        //DBG_FLAGS;
        ixc_route_handle(m);
    }
}

static void ixc_qos_add_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr = (struct netutil_iphdr *)(m->data + m->offset);

    if(ixc_qos.tunnel_isset){
        if(!ixc_qos.tunnel_is_ipv6){
            if(!memcmp(iphdr->dst_addr,ixc_qos.tunnel_addr,4)){
                ixc_qos_send_to_next(m);
                return;
            }
        }
    }

    if(IXC_MBUF_FROM_LAN==m->from) ixc_qos_put(m,iphdr->src_addr[3],iphdr->dst_addr[1],iphdr->dst_addr[2],iphdr->dst_addr[3]);
    // 只对LAN to WAN的流量进行QOS,因为无法控制WAN to LAN的流量
    else ixc_qos_send_to_next(m);
    //else ixc_qos_put(m,iphdr->dst_addr[3],iphdr->src_addr[1],iphdr->src_addr[2],iphdr->src_addr[3]);
}

static void ixc_qos_add_for_ipv6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);

    if(ixc_qos.tunnel_isset){
        if(ixc_qos.tunnel_is_ipv6){
            if(!memcmp(header->dst_addr,ixc_qos.tunnel_addr,16)){
                ixc_qos_send_to_next(m);
                return;
            }
        }
    }
    
    if(IXC_MBUF_FROM_LAN==m->from) ixc_qos_put(m,header->src_addr[15],header->dst_addr[13],header->dst_addr[14],header->dst_addr[15]);
    // 只对LAN to WAN的流量进行QOS,因为无法控制WAN to LAN的流量
    else ixc_qos_send_to_next(m);
    //else ixc_qos_put(m,header->dst_addr[15],header->src_addr[13],header->src_addr[14],header->src_addr[15]);
}

int ixc_qos_init(void)
{
    struct ixc_qos_slot *slot;
    bzero(&ixc_qos, sizeof(struct ixc_qos));
    ixc_qos_is_initialized = 1;
    qos_pkt_num=0;

    for (int n = 0; n < IXC_QOS_SLOT_NUM; n++){
        slot = malloc(sizeof(struct ixc_qos_slot));
        if (NULL == slot){
            ixc_qos_uninit();
            STDERR("cannot create slot for qos\r\n");
            break;
        }
        bzero(slot,sizeof(struct ixc_qos_slot));
        slot->slot=n;
        ixc_qos.slot_objs[n]=slot;
    }
    qos_sysloop=sysloop_add(ixc_qos_sysloop_cb,NULL);
    if(NULL==qos_sysloop){
        ixc_qos_uninit();
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    return 0;
}

void ixc_qos_uninit(void)
{
    if(NULL!=qos_sysloop) sysloop_del(qos_sysloop);
    ixc_qos_is_initialized = 0;
}

void ixc_qos_add(struct ixc_mbuf *m)
{
    if (m->is_ipv6){
        ixc_qos_add_for_ipv6(m);
    }else{
        ixc_qos_add_for_ip(m);
    }
}

void ixc_qos_pop(void)
{
    struct ixc_qos_slot *slot_first=ixc_qos.slot_head;
    struct ixc_qos_slot *slot_obj=slot_first,*t_slot;
    struct ixc_qos_slot *slot_old=ixc_qos.slot_head;
    struct ixc_mbuf *m=NULL,*t;

    while(NULL!=slot_obj){
        m=slot_obj->mbuf_first;

        // 这里需要创建一个临时变量,防止其他节点修改m->next导致内存访问出现问题
        t=m->next;
        /**
        if(IXC_MBUF_FROM_LAN==m->from){
            //DBG_FLAGS;
            if(m->is_ipv6) ixc_addr_map_handle(m);
            else ixc_nat_handle(m);
        }else{
            //DBG_FLAGS;
            ixc_route_handle(m);
        }**/
        ixc_qos_send_to_next(m);

        m=t;
        // 如果数据未发送完毕,那么跳转到下一个
        if(NULL!=m){
            slot_obj->mbuf_first=m;
            slot_old=slot_obj;
            slot_obj=slot_obj->next;
            continue;
        }
        // 重置slot_obj
        slot_obj->is_used=0;
        slot_obj->mbuf_first=NULL;
        slot_obj->mbuf_last=NULL;

        // 如果不是第一个的处置方式
        if(slot_obj!=slot_first){
            slot_old->next=slot_obj->next;
            t_slot=slot_obj->next;
            slot_obj->next=NULL;
            slot_obj=t_slot;
            continue;
        }

        ixc_qos.slot_head=slot_obj->next;
        t_slot=slot_obj->next;
        slot_obj->next=NULL;
        slot_obj=t_slot;
        slot_first=ixc_qos.slot_head;
        slot_old=slot_first;
    }

}

inline
int ixc_qos_have_data(void)
{
    if(NULL!=ixc_qos.slot_head) return 1;
    return 0;
}

int ixc_qos_tunnel_addr_first_set(unsigned char *addr,int is_ipv6)
{
     ixc_qos.tunnel_is_ipv6=is_ipv6;

    if(is_ipv6) memcpy(ixc_qos.tunnel_addr,addr,16);
    else memcpy(ixc_qos.tunnel_addr,addr,4);

    ixc_qos.tunnel_isset=1;

    return 0;
}

void ixc_qos_tunnel_addr_first_unset(void)
{
    ixc_qos.tunnel_isset=0;
}

inline
unsigned long long ixc_qos_pkt_num(void)
{
    return qos_pkt_num;
}