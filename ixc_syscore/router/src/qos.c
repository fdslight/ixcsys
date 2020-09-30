#include <string.h>
#include <arpa/inet.h>

#include "qos.h"
#include "udp_src_filter.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/debug.h"

static struct ixc_qos ixc_qos;
static int ixc_qos_is_initialized = 0;

inline static int ixc_qos_calc_slot(unsigned char a, unsigned char b, unsigned short _id)
{
    unsigned int v= (a << 24) | (b<<16) | _id;
    int slot_num= v % IXC_QOS_SLOT_NUM;

    return slot_num;
}

static void ixc_qos_put(struct ixc_mbuf *m,unsigned c,unsigned char ipproto,int hdr_len)
{
    unsigned short id;
    int slot;
    struct netutil_tcphdr *tcphdr;
    struct netutil_udphdr *udphdr;
    struct ixc_mbuf *mbuf_end;
    struct ixc_qos_slot *slot_obj;

    // 根据协议选择
    switch(ipproto){
        case 7:
            tcphdr=(struct netutil_tcphdr *)(m->data+m->offset+hdr_len);
            id=ntohs(tcphdr->src_port);
            break;
        case 17:
        case 136:
            udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);
            id=ntohs(udphdr->src_port);
            break;
        default:
            id=0;
            break;
    }

    m->next=NULL;

    slot=ixc_qos_calc_slot(c,ipproto,id);
    mbuf_end=ixc_qos.mbuf_slots_end[slot];
    ixc_qos.tot_pkt_num+=1;
    
    // 如果槽已经存在那么直接插入数据即可
    if(NULL!=mbuf_end){
        mbuf_end->next=m;
        ixc_qos.mbuf_slots_end[slot]=m;
        return;
    }

    slot_obj=ixc_qos.empty_slot_head;
    ixc_qos.empty_slot_head=slot_obj->next;

    slot_obj->next=NULL;
    slot_obj->slot=slot;

    ixc_qos.mbuf_slots_head[slot]=m;
    ixc_qos.mbuf_slots_end[slot]=m;
}

static void ixc_qos_add_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr = (struct netutil_iphdr *)(m->data + m->offset);
    int hdr_len=(iphdr->ver_and_ihl & 0x0f) * 4;

    ixc_qos_put(m,iphdr->dst_addr[3],iphdr->protocol,hdr_len);
}

static void ixc_qos_add_for_ipv6(struct ixc_mbuf *m)
{
    ixc_mbuf_put(m);
}

int ixc_qos_init(void)
{
    struct ixc_qos_slot *slot;
    bzero(&ixc_qos, sizeof(struct ixc_qos));
    ixc_qos_is_initialized = 1;

    for (int n = 0; n < IXC_QOS_SLOT_NUM; n++){
        slot = malloc(sizeof(struct ixc_qos_slot));
        if (NULL == slot)
        {
            ixc_qos_uninit();
            STDERR("cannot create slot for qos\r\n");
            break;
        }
        slot->next = ixc_qos.empty_slot_head;
        ixc_qos.empty_slot_head = slot;
    }

    return 0;
}

void ixc_qos_uninit(void)
{
    struct ixc_qos_slot *slot = ixc_qos.empty_slot_head, *t;

    while (NULL != slot)
    {
        t = slot->next;
        free(slot);
        slot = t;
    }

    slot = ixc_qos.used_slots_head;
    while (NULL != slot)
    {
        t = slot->next;
        free(slot);
        slot = t;
    }

    ixc_qos_is_initialized = 0;
}

void ixc_qos_add(struct ixc_mbuf *m, int is_ipv6)
{
    if (is_ipv6)
        ixc_qos_add_for_ipv6(m);
    else
        ixc_qos_add_for_ip(m);
}

void ixc_qos_pop(void)
{
    struct ixc_qos_slot *slot = NULL, *t = NULL;
    struct ixc_mbuf *m;

    t = ixc_qos.used_slots_head;
    slot = ixc_qos.used_slots_head;

    while (NULL != slot){
        m = ixc_qos.mbuf_slots_head[slot->slot];
        ixc_udp_src_filter_handle(m);
        m = m->next;

        ixc_qos.tot_pkt_num-=1;

        if (NULL != m){
            t = slot;
            slot = slot->next;
            ixc_qos.mbuf_slots_head[slot->slot]=NULL;
            ixc_qos.mbuf_slots_end[slot->slot]=NULL;
            continue;
        }
        // 此处回收slot
        // 如果是第一个slot
        if (slot == ixc_qos.used_slots_head){
            ixc_qos.used_slots_head = slot->next;
            slot = slot->next;
            continue;
        }

        t->next = slot->next;
        slot->next = ixc_qos.empty_slot_head;
        ixc_qos.empty_slot_head = slot;
    }
}

int ixc_qos_have_data(void)
{
    if (ixc_qos.tot_pkt_num) return 1;

    return 0;
}

void ixc_qos_udp_udplite_first(int enable)
{
    ixc_qos.udp_udplite_first = enable;
}