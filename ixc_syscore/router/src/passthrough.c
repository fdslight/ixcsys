#include<string.h>
#include<arpa/inet.h>

#include "passthrough.h"
#include "netif.h"
#include "route.h"

#include "../../../pywind/clib/debug.h"

static int passthrough_is_initialized=0;
static struct ixc_passthrough passthrough;

static void __ixc_passthrough_del_cb(void *data)
{
    struct ixc_passthrough_node *node=data;
    int idx;

    if(node->is_passdev){
        idx=node->index;
        passthrough.passdev_nodes[idx]=NULL;
    }

    free(node);
}


int ixc_passthrough_init(void)
{
    struct map *m;
    int rs=map_new(&m,6);
    
    bzero(&passthrough,sizeof(struct ixc_passthrough));

    if(rs){
        STDERR("cannot init passthrough\r\n");
        return -1;
    }

    passthrough.permit_map=m;
    passthrough.count=0;
    passthrough_is_initialized=1;

    return 0;
}

void ixc_passthrough_uninit(void)
{
    passthrough_is_initialized=0;

    map_release(passthrough.permit_map,__ixc_passthrough_del_cb);
}

inline
int ixc_passthrough_is_passthrough_traffic(struct ixc_mbuf *m)
{
    unsigned char *hwaddr;
    int is_brd=0;
    char is_found=0;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return 0;
    }

    // 如果没有任何记录,那么不允许直通,主要针对广播报文
    if(0==passthrough.count) return 0;

    if(IXC_MBUF_FROM_LAN==m->from){
        hwaddr=m->src_hwaddr;
    }else{
        hwaddr=m->dst_hwaddr;
    }

    is_brd=hwaddr[0] & 0x01;
    
    // 源端地址的广播mac地址禁止通过
    if(is_brd && IXC_MBUF_FROM_LAN==m->from) return 0;

    // 当启用IPv6直通功能时禁用IPv6,与IPv6直通功能需要处理路由功能冲突
    if(m->link_proto==0x86dd && ixc_route_is_enabled_ipv6_pass()) return 0;

    // 检查MAC地址是否是多播或者广播地址
    if(!is_brd){
        map_find(passthrough.permit_map,(char *)hwaddr,&is_found);
        if(is_found) return 1;
        return 0;
    }

    // 多播和广播需要直通
    return 1;
}

inline
struct ixc_mbuf *ixc_passthrough_send_auto(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=NULL;
    struct ixc_mbuf *new_mbuf;
    int is_brd;
    unsigned char *hwaddr;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return NULL;
    }

    if(IXC_MBUF_FROM_LAN==m->from){
        hwaddr=m->src_hwaddr;
        netif=ixc_netif_get(IXC_NETIF_WAN);
    }else{
        hwaddr=m->dst_hwaddr;
        netif=ixc_netif_get(IXC_NETIF_LAN);
    }

    is_brd=hwaddr[0] & 0x01;

    // clone的原因为IPv6的多播报文在直通模式需要特殊处理
    if(is_brd && IXC_MBUF_FROM_WAN==m->from){
        new_mbuf=ixc_mbuf_clone(m);
    }else{
        new_mbuf=m;
        m=NULL;
    }

    new_mbuf->netif=netif;
    ixc_netif_send(new_mbuf);

    return m;
}

int ixc_passthrough_device_add(unsigned char *hwaddr,int is_passdev)
{
    int rs;
    char is_found;
    struct ixc_passthrough_node *node,*tmp_node;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return -1;
    }

    if(passthrough.count>=IXC_PASSTHROUGH_DEV_MAX){
        STDERR("limit passthrough device,the number of devices is %d\r\n",IXC_PASSTHROUGH_DEV_MAX);
        return -1;
    }

    map_find(passthrough.permit_map,(char *)hwaddr,&is_found);
    if(is_found) return 0;

    node=malloc(sizeof(struct ixc_passthrough_node));
    if(NULL==node){
        STDERR("cannot malloc for struct ixc_passthrough_node\r\n");
        return -1;
    }

    memcpy(node->hwaddr,hwaddr,6);

    rs=map_add(passthrough.permit_map,(char *)hwaddr,node);

    if(rs){
        STDERR("cannot add passthrough device\r\n");
        free(node);
        return -1;
    }

    passthrough.count+=1;
    node->is_passdev=is_passdev;

    if(!is_passdev) return 0;

    // 把PASS设备放置在数组索引中,便于多播转换成单播
    for(int n=0;n<IXC_PASSTHROUGH_DEV_MAX;n++){
        tmp_node=passthrough.passdev_nodes[n];
        if(NULL==tmp_node){
            passthrough.passdev_nodes[n]=node;
            node->index=n;
            break;
        }
    }

    return 0;
}

void ixc_passthrough_device_del(unsigned char *hwaddr)
{
    char is_found;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
    }

    map_find(passthrough.permit_map,(char *)hwaddr,&is_found);

    if(is_found) passthrough.count-=1;

    map_del(passthrough.permit_map,(char *)hwaddr,__ixc_passthrough_del_cb);
}

void ixc_passthrough_handle_from_passdev(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=NULL;
    struct ixc_mbuf *new_mbuf;
    int is_brd;
    unsigned char *hwaddr;
    struct ixc_passthrough_node *node;
    char is_found;

    if(!passthrough_is_initialized){
        STDERR("not initialized passthrough\r\n");
        return;
    }

    hwaddr=m->dst_hwaddr;
    is_brd=hwaddr[0] & 0x01;

    // 此处发送给LAN网卡
    netif=ixc_netif_get(IXC_NETIF_LAN);
    m->netif=netif;

    if(!is_brd){
        node=map_find(passthrough.permit_map,(char *)hwaddr,&is_found);
        if(!is_found){
            ixc_mbuf_put(m);
            return;
        }
        ixc_netif_send(m);
        return;
    }

    // 去除以太网头部
    m->begin=m->begin+14;
    m->offset=m->begin;

    // 把多播地址转换成单播
    for(int n=0;n<IXC_PASSTHROUGH_DEV_MAX;n++){
        node=passthrough.passdev_nodes[n];
        if(NULL==node) continue;

        // 修改目的以太网头部
        memcpy(m->dst_hwaddr,node->hwaddr,6);

        new_mbuf=ixc_mbuf_clone(m);
        
        if(NULL==new_mbuf){
            STDERR("cannot clone mbuf\r\n");
            continue;
        }

        if(0==passthrough.vlan_id_tagged_for_passdev){
            ixc_ether_send(new_mbuf,1);
            continue;
        }
        
        ixc_ether_send3(new_mbuf,0x8100,passthrough.vlan_id_tagged_for_passdev);
    }

    // 回收旧的mbuf
    ixc_mbuf_put(m);
}

void ixc_passthrough_send2passdev(struct ixc_mbuf *m)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_PASS);
    struct ixc_ether_vlan_header *vlan_header;
    unsigned short vlan_id;
    
    // 可能直通设备未开启
    if(NULL==netif){
        ixc_mbuf_put(m);
        return;
    }

    m->netif=netif;

    // 检查是否开启VLAN,未开启VLAN则直接发送
    if(0==passthrough.vlan_id_tagged_for_passdev){
        ixc_netif_send(m);
        return;
    }

    // 如果开启VLAN之后,那么需要对VLAN进行untag再发送
    if(0x8100!=m->link_proto){
        ixc_mbuf_put(m);
        return;
    }

    vlan_header=(struct ixc_ether_vlan_header *)(m->data+m->begin);
    vlan_id=ntohs(vlan_header->vlan_info) & 0x0fff;

    if(vlan_id!=passthrough.vlan_id_tagged_for_passdev){
        ixc_mbuf_put(m);
        return;
    }

    m->begin=m->offset=m->begin+sizeof(struct ixc_ether_header);
    m->link_proto=ntohs(vlan_header->type);

    // 限制协议
    if(m->link_proto<0x0800){
        ixc_mbuf_put(m);
        return;
    }

    ixc_ether_send(m,1);
}

int ixc_passthrough_is_passthrough2passdev_traffic(unsigned char *hwaddr)
{
    struct ixc_passthrough_node *node;
    char is_found;

    node=map_find(passthrough.permit_map,(char *)hwaddr,&is_found);

    if(NULL==node) return 0;

    return node->is_passdev;
}

int ixc_passthrough_set_vid_for_passdev(unsigned short vid)
{
    if(vid<0 || vid>4094) {
        return -1;
    }
    
    passthrough.vlan_id_tagged_for_passdev=vid;
    return 0;
}