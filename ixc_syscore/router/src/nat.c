#include<string.h>
#include<arpa/inet.h>

#include "nat.h"
#include "pppoe.h"
#include "netif.h"
#include "ether.h"
#include "addr_map.h"
#include "arp.h"
#include "ip.h"
#include "qos.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static int nat_is_initialized=0;
struct ixc_nat nat;
struct time_wheel nat_time_wheel;
struct sysloop *nat_sysloop=NULL;

/// 获取可用的NAT ID
static struct ixc_nat_id *ixc_nat_id_get(struct ixc_nat_id_set *id_set)
{
    struct ixc_nat_id *id=id_set->head;

    if(NULL!=id){
        id_set->head=id->next;
        id->next=NULL;

        return id;
    }

    if(id_set->cur_id>IXC_NAT_ID_MAX) return NULL;

    id=malloc(sizeof(struct ixc_nat_id));

    if(NULL==id){
        STDERR("no memory for malloc struct ixc_nat_id\r\n");
        return NULL;
    }

    id->id=id_set->cur_id;
    id->net_id=htons(id->id);
    id_set->cur_id+=1;

    return id;
}

/// 释放使用过的NAT ID
static void ixc_nat_id_put(struct ixc_nat_id_set *id_set,struct ixc_nat_id *id)
{
    if(NULL==id) return;

    id->next=id_set->head;
    id_set->head=id;
}

static void ixc_nat_del_cb(void *data)
{
    struct ixc_nat_session *s=data;
    struct ixc_nat_id_set *id_set;
    s->refcnt-=1;
    // 引用计数不为0那么直接返回
    if(0!=s) return;

    switch(s->protocol){
        case 1:
            id_set=&(nat.icmp_set);
            break;
        case 7:
            id_set=&(nat.tcp_set);
            break;
        case 17:
        case 136:
            id_set=&(nat.udp_set);
            break;
        default:
            STDERR("system nat protocol bug\r\n");
            break;
    }

    ixc_nat_id_put(id_set,s->nat_id);
    free(s);
}


static struct ixc_mbuf *ixc_nat_do(struct ixc_mbuf *m,int is_src)
{
    struct netutil_iphdr *iphdr;
    unsigned char addr[4];
    int hdr_len=0;
    unsigned short id=0;
    char key[7],tmp[7],is_found;
    struct ixc_nat_session *session;

    unsigned short *csum_ptr,csum;
    unsigned short *id_ptr;

    struct netutil_udphdr *udphdr;
    struct netutil_tcphdr *tcphdr;
    struct netutil_icmpecho *icmpecho;
    struct netutil_icmphdr *icmphdr;
    struct ixc_netif *netif=m->netif;
    struct ixc_nat_id *nat_id=NULL;
    struct ixc_nat_id_set *id_set;

    iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    hdr_len=(iphdr->ver_and_ihl & 0x0f)*4;

    if(is_src) memcpy(addr,iphdr->src_addr,4);
    else memcpy(addr,iphdr->dst_addr,4);

    // 对ICMP进行特殊处理,ICMP只支持echo request和echo reply
    if(1==iphdr->protocol){
        icmphdr=(struct netutil_icmphdr *)(m->data+m->offset+hdr_len);
        if(8!=icmphdr->type || 0!=icmphdr->type){
            ixc_mbuf_put(m);
            return NULL;
        }
    }

    switch(iphdr->protocol){
        case 1:
            icmpecho=(struct netutil_icmpecho *)(m->data+m->offset+hdr_len);
            csum_ptr=&(icmpecho->icmphdr.checksum);
            id_ptr=&(icmpecho->id);
            id_set=&(nat.icmp_set);
            break;
        case 7:
            tcphdr=(struct netutil_tcphdr *)(m->data+m->offset+hdr_len);
            csum_ptr=&tcphdr->csum;
            id_ptr=is_src?&(tcphdr->src_port):&(tcphdr->dst_port);
            id_set=&(nat.tcp_set);
            break;
        case 17:
        case 136:
            udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);
            csum_ptr=&(udphdr->checksum);
            id_ptr=is_src?&(udphdr->src_port):&(udphdr->dst_port);
            id_set=&(nat.udp_set);
            break;
        // 不支持的协议直接丢弃数据包
        default:
            ixc_mbuf_put(m);
            return NULL;
    }

    // 首先检查NAT记录是否存在
    memcpy(key,addr,4);
    key[4]=iphdr->protocol;
    memcpy(key+5,&id,2);

    if(is_src) session=map_find(nat.lan2wan,key,&is_found);
    else session=map_find(nat.wan2lan,key,&is_found);

    // WAN口找不到的那么直接丢弃数据包
    if(NULL==session && !is_src){
        ixc_mbuf_put(m);
        return NULL;
    }

    // 来自于LAN但没有会话记录那么创建session
    if(NULL==session && is_src){
        nat_id=ixc_nat_id_get(id_set);
        if(NULL==nat_id){
            ixc_mbuf_put(m);
            STDERR("cannot get NAT ID for protocol %d\r\n",iphdr->protocol);
            return NULL;
        }

        session=malloc(sizeof(struct ixc_nat_session));
        if(NULL==session){
            ixc_mbuf_put(m);
            ixc_nat_id_put(id_set,nat_id);
            STDERR("no memory for malloc struct ixc_nat_session\r\n");
            return NULL;
        }

        memcpy(session->lan_key,key,7);
        // LAN to WAN映射添加
        if(0!=map_add(nat.lan2wan,key,session)){
            ixc_mbuf_put(m);
            ixc_nat_id_put(id_set,nat_id);

            STDERR("nat map add failed\r\n");
            return NULL;
        }

        memcpy(tmp,key,7);
        memcpy(tmp+5,&(nat_id->id),2);
        memcpy(session->wan_key,tmp,7);

        if(0!=map_add(nat.wan2lan,tmp,session)){
            free(session);
            ixc_mbuf_put(m);
            ixc_nat_id_put(id_set,nat_id);
            map_del(nat.lan2wan,key,NULL);
            STDERR("nat map add failed\r\n");
            return NULL;
        }

        session->refcnt=2;

        session->nat_id=nat_id;
        session->lan_id=*id_ptr;
        session->wan_id=nat_id->net_id;

        session->protocol=iphdr->protocol;

        memcpy(session->addr,iphdr->src_addr,4);
    }

    if(!is_src){
        rewrite_ip_addr(iphdr,session->addr,is_src);
        csum=csum_calc_incre(*id_ptr,session->lan_id,*csum_ptr);
        session->up_time=time(NULL);
    }else {
        rewrite_ip_addr(iphdr,netif->ipaddr,is_src);
        csum=csum_calc_incre(*id_ptr,session->wan_id,*csum_ptr);
    }

    *csum_ptr=csum;

    return m;
}

static void ixc_nat_handle_from_wan(struct ixc_mbuf *m)
{   
    // 没有开启NAT那么直接发送数据包
    if(!nat.enable){
        ixc_qos_add(m);
        return;
    }

    m=ixc_nat_do(m,0);
    if(NULL==m) return;

    ixc_qos_add(m);
}

static void ixc_nat_handle_from_lan(struct ixc_mbuf *m)
{
    // 未开启NAT那么直接发送数据包
    if(!nat.enable){
        ixc_pppoe_handle(m);
        return;
    }

    DBG_FLAGS;
    m=ixc_nat_do(m,1);
    if(NULL==m) return;
}

static void ixc_nat_timeout_cb(void *data)
{
    struct ixc_nat_session *session=data;
    struct time_data *tdata;
    time_t now_time=time(NULL);

    // 如果NAT会话超时那么就删除数据
    if(now_time-session->up_time>IXC_NAT_TIMEOUT){
        map_del(nat.wan2lan,(char *)(session->wan_key),ixc_nat_del_cb);
        map_del(nat.lan2wan,(char *)(session->lan_key),ixc_nat_del_cb);
        return;
    }
    
    // 处理未超时的情况
    tdata=time_wheel_add(&nat_time_wheel,session,now_time-session->up_time);
    if(NULL==tdata){
        STDERR("cannot add to time wheel\r\n");
        return;
    }
}

static void ixc_nat_sysloop_cb(struct sysloop *lp)
{
    //  如果NAT没有被开启那么直接跳过
    if(!nat.enable) return;
    // 执行时间函数,定期检查NAT会话是否过期
    time_wheel_handle(&nat_time_wheel);
}

int ixc_nat_init(void)
{
    struct map *m;
    int rs;

    bzero(&nat,sizeof(struct ixc_nat));

    nat.icmp_set.cur_id=IXC_NAT_ID_MIN;
    nat.tcp_set.cur_id=IXC_NAT_ID_MIN;
    nat.udp_set.cur_id=IXC_NAT_ID_MIN;

    rs=time_wheel_new(&nat_time_wheel,(IXC_NAT_TIMEOUT/10)+8,10,ixc_nat_timeout_cb,2048);

    if(0!=rs){
        STDERR("cannot create time wheel\r\n");
        return -1;
    }

    rs=map_new(&m,7);
    if(rs){
        time_wheel_release(&nat_time_wheel);
        STDERR("cannot init map\r\n");
        return -1;
    }
    nat.lan2wan=m;
    rs=map_new(&m,7);
    if(rs){
        map_release(nat.lan2wan,NULL);
        time_wheel_release(&nat_time_wheel);
        STDERR("cannot init map\r\n");
        return -1;
    }
    nat.wan2lan=m;

    nat_is_initialized=1;
    nat_sysloop=sysloop_add(ixc_nat_sysloop_cb,NULL);

    return 0;
}

void ixc_nat_uninit(void)
{
    nat_is_initialized=0;

    return;
}

void ixc_nat_handle(struct ixc_mbuf *m)
{
    
    if(!nat_is_initialized){
        ixc_mbuf_put(m);
        STDERR("please init nat\r\n");
        return;
    }

    if(IXC_MBUF_FROM_LAN==m->from) ixc_nat_handle_from_lan(m);
    else ixc_nat_handle_from_wan(m);
}

int ixc_nat_enable(int status,int type)
{
    nat.enable=status;
    
    return 0;
}