#include <string.h>
#include <arpa/inet.h>

#include "qos.h"
#include "nat.h"
#include "nat66.h"
#include "route.h"
#include "addr_map.h"
#include "debug.h"
#include "netif.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static struct ixc_qos ixc_qos;
static int ixc_qos_is_initialized = 0;
static struct sysloop *qos_sysloop=NULL;

static void ixc_qos_sysloop_cb(struct sysloop *lp)
{
    while(ixc_netif_wan_sendable() && ixc_qos_have_data()) ixc_qos_pop();
}

inline static int ixc_qos_calc_slot(void *header,int is_ipv6)
{
    struct netutil_iphdr *iphdr;
    struct netutil_ip6hdr *ip6hdr;
    struct netutil_udphdr *udphdr;
    int hdr_len;

    unsigned long long v;
    unsigned char next_header,*s=header;
    unsigned char buf[8]={
        0,0,0,0,
        0,0,0,0
    };

    if(is_ipv6){
        ip6hdr=header;
        next_header=ip6hdr->next_header;
        hdr_len=40;
        
        buf[0]=ip6hdr->src_addr[14];
        buf[1]=ip6hdr->src_addr[15];
        buf[2]=ip6hdr->dst_addr[14];
        buf[3]=ip6hdr->dst_addr[15];
    }else{
        iphdr=header;
        next_header=iphdr->protocol;
        hdr_len=(iphdr->ver_and_ihl & 0x0f) * 4;

        buf[0]=iphdr->src_addr[2];
        buf[1]=iphdr->src_addr[3];
        buf[2]=iphdr->dst_addr[2];
        buf[3]=iphdr->dst_addr[3];
    }

    switch (next_header){
        case 6:
        case 17:
        case 136:
            // TCP头部,UDP和UDPLite端口部分定义相同,这里只需要端口部分,直接用UDP协议定义即可
            udphdr=(struct netutil_udphdr *)(s+hdr_len);
            
            memcpy(&buf[4],&(udphdr->src_port),2);
            memcpy(&buf[6],&(udphdr->dst_port),2);
        default:
            break;
    }
    
    memcpy(&v,buf,8);

    return v % IXC_QOS_SLOT_NUM;
}

static void ixc_qos_put(struct ixc_mbuf *m,void *header,int is_ipv6)
{
    int slot_no;
    struct ixc_qos_slot *slot_obj;

    m->next=NULL;
    slot_no=ixc_qos_calc_slot(header,is_ipv6);
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

static void ixc_qos_send_to_next(struct ixc_mbuf *m)
{
    if(IXC_MBUF_FROM_LAN==m->from){
        //DBG_FLAGS;
        if(m->is_ipv6){
            ixc_addr_map_handle(m);
        }else{
            ixc_nat_handle(m);
        }
    }else{
        //DBG_FLAGS;
        ixc_route_handle(m);
    }
}

static void ixc_qos_add_for_ip(struct ixc_mbuf *m)
{
    struct netutil_iphdr *iphdr = (struct netutil_iphdr *)(m->data + m->offset);
    int size,is_first=0;
    //struct ixc_addr_map_record *addr_map_record;

    // 只对LAN to WAN的流量进行QOS,因为无法控制WAN to LAN的流量
    if(IXC_MBUF_FROM_WAN==m->from){
        ixc_qos_send_to_next(m);
        return;
    }

    // 隧道流量优先
    if(ixc_qos.tunnel_isset){
        if(!ixc_qos.tunnel_is_ipv6){
            if(!memcmp(iphdr->src_addr,ixc_qos.tunnel_addr,4)) is_first=1;
        }
    }

    size=m->tail-m->offset;

    if(size<=ixc_qos.qos_mpkt_first_size) is_first=1;
    if(is_first){
        ixc_qos_send_to_next(m);
    }else{
        ixc_qos_put(m,iphdr,0);
    }
}

static void ixc_qos_add_for_ipv6(struct ixc_mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    //struct ixc_addr_map_record *addr_map_record;
    int size,is_first=0;

    // 只对LAN to WAN的流量进行QOS,因为无法控制WAN to LAN的流量
    if(IXC_MBUF_FROM_WAN==m->from){
        ixc_nat66_prefix_modify(m,0);
        ixc_qos_send_to_next(m);
        return;
    }

    // 隧道流量优先
    if(ixc_qos.tunnel_isset){
        if(ixc_qos.tunnel_is_ipv6){
            if(!memcmp(header->src_addr,ixc_qos.tunnel_addr,16)) is_first=1;
        }
    }

    ixc_nat66_prefix_modify(m,1);

    size=m->tail-m->offset;
    if(size<=ixc_qos.qos_mpkt_first_size) is_first=1;

    if(is_first){
        ixc_qos_send_to_next(m);
    }else{
        ixc_qos_put(m,header,1);
    }
    
}

int ixc_qos_init(void)
{
    struct ixc_qos_slot *slot;
    struct map *m;
    int is_err;

    bzero(&ixc_qos, sizeof(struct ixc_qos));

    ixc_qos_is_initialized = 1;
    // 小于0表示不设置小包优先策略
    ixc_qos.qos_mpkt_first_size=0;

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

    is_err=map_new(&m,6);
    if(is_err){
        STDERR("cannot create map for qos\r\n");
        return -1;
    }

    ixc_qos.first_host_hwaddr_map=m;

    return 0;
}

void ixc_qos_uninit(void)
{
    if(NULL!=qos_sysloop) sysloop_del(qos_sysloop);
    if(NULL!=ixc_qos.first_host_hwaddr_map){
        map_release(ixc_qos.first_host_hwaddr_map,NULL);
    }
    ixc_qos_is_initialized = 0;
}

void ixc_qos_add(struct ixc_mbuf *m)
{
    if(IXC_MBUF_FROM_LAN==m->from){
        if(ixc_qos_is_first_host(m->orig_src_hwaddr)){
            if(m->is_ipv6) ixc_nat66_prefix_modify(m,1);
            ixc_qos_send_to_next(m);
            return;
        }
    }

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

int ixc_qos_mpkt_first_set(int size)
{
    
    if(size<=0){
        ixc_qos.qos_mpkt_first_size=0;
        return 0;
    }

    // 限制小包最大值
    if(size<64 || size>512){
        return -1;
    }

    ixc_qos.qos_mpkt_first_size=size;

    return 0;
}

/// 增加优先主机
int ixc_qos_add_first_host(const unsigned char *hwaddr)
{
    char is_found;
    int is_err;
    map_find(ixc_qos.first_host_hwaddr_map,(char *)hwaddr,&is_found);

    if(is_found) return 0;

    is_err=map_add(ixc_qos.first_host_hwaddr_map,(char *)hwaddr,NULL);
    
    return is_err;
}

/// 删除优先主机
void ixc_qos_del_first_host(const unsigned char *hwaddr)
{
    map_del(ixc_qos.first_host_hwaddr_map,(char *)hwaddr,NULL);
}

int ixc_qos_is_first_host(const unsigned char *hwaddr)
{
    char is_found;
    map_find(ixc_qos.first_host_hwaddr_map,(char *)hwaddr,&is_found);

    return is_found;
}