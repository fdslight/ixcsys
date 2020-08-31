#include<string.h>

#include "qos.h"
#include "p2p.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"

static struct ixc_qos ixc_qos;
static int ixc_qos_is_initialized=0;

static int ixc_qos_calc_slot(unsigned char a,unsigned char b,unsigned short _id)
{
    return 0;
}

static void ixc_qos_add_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset);



}


static void ixc_qos_add_for_ipv6(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}


int ixc_qos_init(void)
{
    struct ixc_qos_slot *slot;
    bzero(&ixc_qos,sizeof(struct ixc_qos));
    ixc_qos_is_initialized=1;

    for(int n=0;n<IXC_QOS_SLOT_NUM;n++){
        slot=malloc(sizeof(struct ixc_qos_slot));
        if(NULL==slot){
            ixc_qos_uninit();
            STDERR("cannot create slot for qos\r\n");
            break;
        }
        slot->next=ixc_qos.empty_slot_head;
        ixc_qos.empty_slot_head=slot;
    }
    
    return 0;
}

void ixc_qos_uninit(void)
{
    struct ixc_qos_slot *slot=ixc_qos.empty_slot_head,*t;

    while(NULL!=slot){
        t=slot->next;
        free(slot);
        slot=t;
    }

    slot=ixc_qos.used_slots;
    while(NULL!=slot){
        t=slot->next;
        free(slot);
        slot=t;
    }

    ixc_qos_is_initialized=0;
}

void ixc_qos_add(struct ixc_mbuf *m,int is_ipv6)
{
    if(is_ipv6) ixc_qos_add_for_ipv6(m);
    else ixc_qos_add_for_ip(m);
}

void ixc_qos_pop(void)
{
    struct ixc_qos_slot *slot=NULL,*t=NULL;
    struct ixc_mbuf *m;

    slot=ixc_qos.used_slots;

    while(NULL!=slot){
        m=ixc_qos.mbuf_slots[slot->slot];
        ixc_p2p_handle(m);
        m=m->next;

        if(NULL!=m){
            slot=slot->next;
            continue;
        }
        // 此处回收slot
        
    }
}

int ixc_qos_have_data(void)
{
    if(ixc_qos.tot_pkt_num) return 1;

    return 0;
}

void ixc_qos_udp_udplite_first(int enable)
{
    ixc_qos.udp_udplite_first=enable;
}