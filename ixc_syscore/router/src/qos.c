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

static void ixc_qos_sysloop_cb(struct sysloop *lp)
{
    // 弹出数据包
    ixc_qos_pop();
}

inline static int ixc_qos_calc_slot(unsigned char a, unsigned char b, unsigned short _id)
{
    unsigned int v= (a << 24) | (b<<16) | _id;
    int slot_num= v % IXC_QOS_SLOT_NUM;

    return slot_num;
}

static void ixc_qos_put(struct ixc_mbuf *m,unsigned c,unsigned char ipproto)
{
    unsigned short id=0;
    int slot_no;
    struct ixc_qos_slot *slot_obj;

    m->next=NULL;
    slot_no=ixc_qos_calc_slot(c,ipproto,id);
    slot_obj=ixc_qos.slot_objs[slot_no];

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

static void ixc_qos_add_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr = (struct netutil_iphdr *)(m->data + m->offset);

    ixc_qos_put(m,iphdr->dst_addr[3],iphdr->protocol);
}

static void ixc_qos_add_for_ipv6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);

    ixc_qos_put(m,header->dst_addr[15],header->next_header);
}

int ixc_qos_init(void)
{
    struct ixc_qos_slot *slot;
    bzero(&ixc_qos, sizeof(struct ixc_qos));
    ixc_qos_is_initialized = 1;

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
    struct ixc_qos_slot *slot_obj=slot_first;
    struct ixc_qos_slot *slot_old=ixc_qos.slot_head;
    struct ixc_mbuf *m=NULL,*t;

    while(NULL!=slot_obj){
        m=slot_obj->mbuf_first;

        // 这里需要创建一个临时变量,防止其他节点修改m->next导致内存访问出现问题
        t=m->next;

        if(IXC_MBUF_FROM_LAN==m->from){
            //DBG_FLAGS;
            if(m->is_ipv6) ixc_addr_map_handle(m);
            else ixc_nat_handle(m);
        }else{
            //DBG_FLAGS;
            ixc_route_handle(m);
        }
        m=t;
        // 如果数据未发生完毕,那么跳转到下一个
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
            slot_old=slot_obj;
            slot_obj=slot_obj->next;
            continue;
        }

        ixc_qos.slot_head=slot_obj->next;
        slot_obj=slot_obj->next;
        slot_first=ixc_qos.slot_head;
        slot_old=slot_first;
    }

}

int ixc_qos_have_data(void)
{
    if(NULL!=ixc_qos.slot_head) return 1;
    return 0;
}

void ixc_qos_udp_udplite_first(int enable)
{
    ixc_qos.udp_udplite_first = enable;
}