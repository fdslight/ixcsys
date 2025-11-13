#include<string.h>
#include<arpa/inet.h>

#include "nat.h"
#include "netif.h"
#include "ether.h"
#include "addr_map.h"
#include "arp.h"
#include "ip.h"
#include "debug.h"
#include "route.h"
#include "ipunfrag.h"
#include "port_map.h"
#include "router.h"
#include "qos.h"

#include "../../../pywind/clib/netutils.h"
#include "../../../pywind/clib/sysloop.h"

static int nat_is_initialized=0;
struct ixc_nat nat;
struct time_wheel nat_time_wheel;
struct sysloop *nat_sysloop=NULL;


/// 查找是否在端口映射记录中
static struct ixc_port_map_record *ixc_nat_port_map_get(struct ixc_mbuf *m,int from_wan)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct netutil_tcphdr *tcphdr=NULL;
    struct netutil_udphdr *udphdr=NULL;
    struct ixc_port_map_record *r=NULL;

    unsigned short port;

    int header_len=(header->ver_and_ihl & 0x0f)*4;
    
    switch(header->protocol){
        case 6:
            tcphdr=(struct netutil_tcphdr *)(m->data+m->offset+header_len);
            port=from_wan?tcphdr->dst_port:tcphdr->src_port;
            r=ixc_port_map_find(header->protocol,port);
            break;
        case 17:
        case 136:
            udphdr=(struct netutil_udphdr *)(m->data+m->offset+header_len);
            port=from_wan?udphdr->dst_port:udphdr->src_port;
            r=ixc_port_map_find(header->protocol,port);
            break;
        default:
            break;
    }

    return r;
}

/// 对IP数据包进行分片并发送
static void ixc_nat_ipfrag_send(struct ixc_mbuf *m,int from_wan)
{
    struct netutil_iphdr *iphdr=(struct netutil_iphdr *)(m->data+m->offset),*tmp_iphdr;
    struct ixc_netif *netif=m->netif;

    int hdr_len=(iphdr->ver_and_ihl & 0x0f)*4;
    // IP数据内容长度
    int ipdata_len=m->tail-m->offset-hdr_len;
    // 每片数据的大小必须未8的倍数
    int slice_size=(netif->mtu_v4-hdr_len)/8*8;
    int cur_len=0,data_size=0,mf=0x2000,df=0x0000;
    unsigned short tot_len,offset=0,csum,frag_info;
    struct ixc_mbuf *new_mbuf=NULL;

    // 检查是否需要分片,不需要分片那么直接发送数据
    if(m->tail-m->offset<=netif->mtu_v4){
        if(from_wan) ixc_qos_add(m);
        else ixc_addr_map_handle(m);
        
        return;
    }

    m->offset+=hdr_len;

    //DBG("%d %d\r\n",slice_size,ipdata_len);

    while (cur_len<ipdata_len){
        new_mbuf=ixc_mbuf_get();

        if(NULL==new_mbuf){
            STDERR("cannot get mbuf\r\n");
            break;
        }

        // 计算出当前的数据大小
        data_size=ipdata_len-cur_len;
        if(data_size>slice_size) data_size=slice_size;
        else mf=0x0000;

        frag_info=df | mf | offset;

        // 设置mbuf的值
        new_mbuf->next=NULL;
        new_mbuf->netif=m->netif;
        new_mbuf->priv_data=m->priv_data;
        new_mbuf->priv_flags=m->priv_flags;
        new_mbuf->is_ipv6=m->is_ipv6;
        new_mbuf->from=m->from;
        new_mbuf->begin=IXC_MBUF_BEGIN;
        new_mbuf->offset=IXC_MBUF_BEGIN;
        new_mbuf->link_proto=m->link_proto;

        memcpy(new_mbuf->next_host,m->next_host,16);
        memcpy(new_mbuf->dst_hwaddr,m->dst_hwaddr,6);
        memcpy(new_mbuf->src_hwaddr,m->src_hwaddr,6);

        // 首先复制头部
        memcpy(new_mbuf->data+new_mbuf->offset,iphdr,hdr_len);
        tmp_iphdr=(struct netutil_iphdr *)(new_mbuf->data+new_mbuf->offset);

        // 计算当前分片大小
        tot_len=hdr_len+data_size;
        
        tmp_iphdr->tot_len=htons(tot_len);
        tmp_iphdr->frag_info=htons(frag_info);
        tmp_iphdr->checksum=0;
        
        // 重新计算IP头部
        csum=csum_calc((unsigned short *)tmp_iphdr,hdr_len);
        tmp_iphdr->checksum=csum;

        // 复制数据
        memcpy(new_mbuf->data+new_mbuf->offset+hdr_len,m->data+m->offset,data_size);

        new_mbuf->tail=new_mbuf->offset+tot_len;
        new_mbuf->end=new_mbuf->tail;

        m->offset+=data_size;
        offset+=data_size/8;
        cur_len+=data_size;

        if(from_wan) ixc_qos_add(new_mbuf);
        else ixc_addr_map_handle(new_mbuf);
    }

    // 回收传入的mbuf
    ixc_mbuf_put(m);
}

/// 获取可用的NAT ID
static struct ixc_nat_id *ixc_nat_id_get(struct ixc_nat_id_set *id_set,unsigned char protocol)
{
    struct ixc_nat_id *id=id_set->head,*prev_id;
    
    prev_id=id;
    for(int n=0;NULL!=id;n++){
        // 和端口映射存在冲突那么跳过
        if(NULL!=ixc_port_map_find(protocol,id->id)){
            prev_id=id;
            id=id->next;
            continue;
        }

        if(0==n) id_set->head=id->next;
        else prev_id->next=id->next;

        id->next=NULL;

        return id;
    }

    if(id_set->cur_id>id_set->id_max) return NULL;

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

    // 检查NAT ID范围是否变更,如果发生变更不在范围内的NAT ID将会被丢弃
    if(id->id<id_set->id_min){
        free(id);
        return;
    }
    if(id->id>id_set->id_max){
        free(id);
        return;
    }

    id->next=id_set->head;
    id_set->head=id;
}

static void ixc_nat_del_cb(void *data)
{
    struct ixc_nat_session *s=data;
    struct ixc_nat_id_set *id_set=NULL;
    struct time_data *tdata=s->tdata;

    s->refcnt-=1;
    
    // 引用计数不为0那么直接返回
    if(s->refcnt!=0) return;

    switch(s->protocol){
        case 1:
            id_set=&(nat.icmp_set);
            break;
        case 6:
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

    IXC_PRINT_IP("nat session delete",s->addr);
    
    if(NULL!=id_set){
        ixc_nat_id_put(id_set,s->nat_id);
    }
    
    if(NULL!=tdata) tdata->is_deleted=1;
    
    free(s);
}


static struct ixc_mbuf *ixc_nat_do(struct ixc_mbuf *m,int is_src)
{
    struct netutil_iphdr *iphdr,*tmp_iphdr;
    unsigned char addr[4]={0,0,0,0};
    int hdr_len=0,tmp_hdr_len,length,is_not_icmp_echo_reply=0;
    char key[7],tmp[7],is_found;
    struct ixc_nat_session *session;
    //unsigned short offset,frag_off;

    unsigned short *csum_ptr,csum;
    unsigned short *id_ptr;

    struct netutil_udphdr *udphdr=NULL;
    struct netutil_tcphdr *tcphdr=NULL;
    unsigned short tcp_header_len_and_flag;
    int tcp_is_syn=0;
    struct netutil_icmpecho *icmpecho;
    struct netutil_icmphdr *icmphdr=NULL;
    struct ixc_netif *netif=m->netif;
    struct ixc_nat_id *nat_id=NULL;
    struct ixc_nat_id_set *id_set;
    struct time_data *tdata;

    iphdr=(struct netutil_iphdr *)(m->data+m->offset);
    tmp_iphdr=iphdr;
    hdr_len=(iphdr->ver_and_ihl & 0x0f)*4;

    //frag_off=ntohs(iphdr->frag_info);
    //offset=frag_off & 0x1fff;
    //df=frag_off & 0x4000;
    
    // 如果是LAN to WAN并且不是第一个数据包直接修改源包地址
    /*if(offset!=0 && is_src){
        rewrite_ip_addr(iphdr,netif->ipaddr,is_src);
        return m;
    }*/

    if(is_src) memcpy(addr,iphdr->src_addr,4);
    // 目标地址为4个0,因为考虑目标地址可能会变,而地址变化后NAT会话并不会被删除
    //else memset(addr,0,4);
    //else memcpy(addr,iphdr->dst_addr,4);

    // 对ICMP进行特殊处理,ICMP只支持echo request和echo reply
    if(1==iphdr->protocol){
        icmphdr=(struct netutil_icmphdr *)(m->data+m->offset+hdr_len);
        if(is_src){
            // LAN出去只支持echo request以及echo reply
            if(8!=icmphdr->type && 0!=icmphdr->type){
                ixc_mbuf_put(m);
                return NULL;
            }
        }else{
            //DBG_FLAGS;
            // 处理WAN的非ICMP echo reply数据包
            if(8!=icmphdr->type &&  0!=icmphdr->type){
                if(icmphdr->type!=3 && icmphdr->type!=11 && icmphdr->type!=12 && icmphdr->type!=4){
                    ixc_mbuf_put(m);
                    return NULL;
                }
                //DBG_FLAGS;
                length=m->tail-m->offset-hdr_len;
                // 检查长度是否合法
                if(length<36){
                    ixc_mbuf_put(m);
                    return NULL;
                }

                
                iphdr=(struct netutil_iphdr *)(m->data+m->offset+hdr_len+8);
                tmp_hdr_len=(iphdr->ver_and_ihl & 0x0f)*4;
            
                if(tmp_hdr_len+8>length){
                    ixc_mbuf_put(m);
                    return NULL;
                }
                // 此处重新修改长度
                hdr_len=hdr_len+8+tmp_hdr_len;
                is_not_icmp_echo_reply=1;
                //DBG("protocol %d\r\n",iphdr->protocol);
            }
        }
    }

    switch(iphdr->protocol){
        case 1:
            icmpecho=(struct netutil_icmpecho *)(m->data+m->offset+hdr_len);
            csum_ptr=&(icmpecho->icmphdr.checksum);
            id_ptr=&(icmpecho->id);
            id_set=&(nat.icmp_set);
            break;
        case 6:
            tcphdr=(struct netutil_tcphdr *)(m->data+m->offset+hdr_len);
            csum_ptr=&tcphdr->csum;
            if(!is_not_icmp_echo_reply) id_ptr=is_src?&(tcphdr->src_port):&(tcphdr->dst_port);
            else id_ptr=is_src?&(tcphdr->dst_port):&(tcphdr->src_port);
            id_set=&(nat.tcp_set);
            break;
        case 17:
        case 136:
            udphdr=(struct netutil_udphdr *)(m->data+m->offset+hdr_len);
            csum_ptr=&(udphdr->checksum);
            if(!is_not_icmp_echo_reply) id_ptr=is_src?&(udphdr->src_port):&(udphdr->dst_port);
            else id_ptr=is_src?&(udphdr->dst_port):&(udphdr->src_port);
            id_set=&(nat.udp_set);
            //DBG("%d\r\n",htons(*id_ptr));
            break;
        // 不支持的协议直接丢弃数据包
        default:
            ixc_mbuf_put(m);
            return NULL;
    }

    // 首先检查NAT记录是否存在
    memcpy(key,addr,4);
    key[4]=iphdr->protocol;
    memcpy(key+5,id_ptr,2);

    if(is_src) session=map_find(nat.lan2wan,key,&is_found);
    // wan2lan只需要三个字节
    else session=map_find(nat.wan2lan,key+4,&is_found);

    // WAN口找不到的那么直接丢弃数据包
    if(NULL==session && !is_src){
        ixc_mbuf_put(m);
        //DBG("%d\r\n  AA",ntohs(*id_ptr));
        return NULL;
    }

    if(6==iphdr->protocol){
        tcp_header_len_and_flag=ntohs(tcphdr->header_len_and_flag);
        tcp_is_syn=(tcp_header_len_and_flag & 0x0002) >> 1;
    }
    // 来自于LAN但没有会话记录那么创建session
    if(NULL==session && is_src){
        // 针对tcp的syn状态进行处理
        if(6==iphdr->protocol){
            if(!tcp_is_syn){
                ixc_mbuf_put(m);
                return NULL;
            }
        }
        nat_id=ixc_nat_id_get(id_set,iphdr->protocol);
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

        bzero(session,sizeof(struct ixc_nat_session));
        tdata=time_wheel_add(&nat_time_wheel,session,IXC_IO_WAIT_TIMEOUT);

        if(NULL==tdata){
            ixc_nat_id_put(id_set,nat_id);
            ixc_mbuf_put(m);
            free(session);
            STDERR("cannot add to time wheel\r\n");
            return NULL;
        }

        session->tdata=tdata;
        tdata->data=session;
        memcpy(session->lan_key,key,7);
        
        // LAN to WAN映射添加
        if(0!=map_add(nat.lan2wan,key,session)){
            ixc_mbuf_put(m);
            ixc_nat_id_put(id_set,nat_id);
            free(session);
            tdata->is_deleted=1;
            STDERR("nat map add failed\r\n");
            return NULL;
        }
        //memset(tmp,0,4);
        //memcpy(tmp,netif->ipaddr,4);
        tmp[0]=iphdr->protocol;
        memcpy(tmp+1,&(nat_id->net_id),2);
        memcpy(session->wan_key,tmp,3);

        if(0!=map_add(nat.wan2lan,tmp,session)){
            tdata->is_deleted=1;
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

        session->min_timeout_flags=0;
        
        // 根据状态减少超时时间
        if(6!=iphdr->protocol){
            // ICMP使用最小时间标记
            if(1==iphdr->protocol){
                session->min_timeout_flags=1;
            }
        }else{
            // 这里肯定是TCP SYN,TCP SYN使用最小超时时间
            session->min_timeout_flags=1;
        }
    }

    if(!is_src){
        if(is_not_icmp_echo_reply) {
            // 重写ICMP非echo relay携带的IP数据
            hdr_len=(tmp_iphdr->ver_and_ihl & 0x0f)*4;
            length=ntohs(tmp_iphdr->tot_len);
            icmphdr=(struct netutil_icmphdr *)(m->data+m->offset+hdr_len);

            rewrite_ip_addr(iphdr,session->addr,1);
            
            csum=csum_calc_incre(*id_ptr,session->lan_id,*csum_ptr);
            *id_ptr=session->lan_id;

            icmphdr->checksum=0;
            csum=csum_calc((unsigned short *)(m->data+m->offset+hdr_len),length-hdr_len);
            icmphdr->checksum=csum;
        }

        iphdr=tmp_iphdr;
        rewrite_ip_addr(iphdr,session->addr,is_src);

        if(!is_not_icmp_echo_reply){
            csum=csum_calc_incre(*id_ptr,session->lan_id,*csum_ptr);
            *id_ptr=session->lan_id;
        }

    }else {
        rewrite_ip_addr(iphdr,netif->ipaddr,is_src);
        csum=csum_calc_incre(*id_ptr,session->wan_id,*csum_ptr);
        *id_ptr=session->wan_id;
        session->up_time=time(NULL);
        if(6==iphdr->protocol){
            if(!tcp_is_syn) session->min_timeout_flags=0;
        }
    }

    if(!is_not_icmp_echo_reply) *csum_ptr=csum;

    return m;
}

static void ixc_nat_handle_from_wan(struct ixc_mbuf *m)
{
    struct ixc_port_map_record *port_map_record=ixc_nat_port_map_get(m,1);
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);

    // 首先检查端口映射记录是否存在,若存在那么就重写IP地址
    if(NULL!=port_map_record){
        rewrite_ip_addr(header,port_map_record->address,0);
    }else{
        m=ixc_nat_do(m,0);
        if(NULL==m) return;
    }
    
    if(m->netif->mtu_v4>=m->tail-m->offset){
        ixc_qos_add(m);
    }else{
        //DBG_FLAGS;
        ixc_nat_ipfrag_send(m,1);
    }
}

static void ixc_nat_handle_from_lan(struct ixc_mbuf *m)
{
    struct ixc_port_map_record *port_map_record=ixc_nat_port_map_get(m,0);
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int pm_flags=0;

    // 如果在端口映射记录中那么就只重写源IP地址
    if(NULL!=port_map_record){
        // 检查端口是否对应主机
        if(!memcmp(header->src_addr,port_map_record->address,4)){
            pm_flags=1;
        }
    }

    if(pm_flags){
         rewrite_ip_addr(header,m->netif->ipaddr,1);
    }else{
        m=ixc_nat_do(m,1);
        if(NULL==m) return;
    }
    
    ixc_nat_ipfrag_send(m,0);
    //ixc_addr_map_handle(m);
}

static void ixc_nat_timeout_cb(void *data)
{
    struct ixc_nat_session *session=data;
    struct time_data *tdata=NULL;
    time_t now_time=time(NULL);
    int timeout=session->min_timeout_flags?IXC_NAT_MIN_TIMEOUT:IXC_NAT_TIMEOUT;

    //DBG_FLAGS;

    //session->tdata=NULL;

    // 如果NAT会话超时那么就删除数据
    if(now_time-session->up_time>=timeout){
        IXC_PRINT_IP("nat session timeout",session->addr);
        map_del(nat.wan2lan,(char *)(session->wan_key),ixc_nat_del_cb);
        map_del(nat.lan2wan,(char *)(session->lan_key),ixc_nat_del_cb);
        return;
    }
    
    //DBG_FLAGS;
    // 处理未超时的情况
    tdata=time_wheel_add(&nat_time_wheel,session,IXC_IO_WAIT_TIMEOUT);

    if(NULL!=tdata){
        //DBG_FLAGS;
        tdata->data=session;
        session->tdata=tdata;
        return;
    }
    
    map_del(nat.wan2lan,(char *)(session->wan_key),ixc_nat_del_cb);
    map_del(nat.lan2wan,(char *)(session->lan_key),ixc_nat_del_cb);

    STDERR("cannot add to time wheel\r\n");
}

static void ixc_nat_sysloop_cb(struct sysloop *lp)
{
    //DBG_FLAGS;
    // 执行时间函数,定期检查NAT会话是否过期
    time_wheel_handle(&nat_time_wheel);
}

int ixc_nat_init(void)
{
    struct map *m;
    int rs;

    bzero(&nat,sizeof(struct ixc_nat));

    nat.icmp_set.cur_id=IXC_NAT_ID_MIN;
    nat.icmp_set.id_min=IXC_NAT_ID_MIN;
    nat.icmp_set.id_max=IXC_NAT_ID_MAX;

    nat.tcp_set.cur_id=IXC_NAT_ID_MIN;
    nat.tcp_set.id_min=IXC_NAT_ID_MIN;
    nat.tcp_set.id_max=IXC_NAT_ID_MAX;

    nat.udp_set.cur_id=IXC_NAT_ID_MIN;
    nat.udp_set.id_min=IXC_NAT_ID_MIN;
    nat.udp_set.id_max=IXC_NAT_ID_MAX;

    nat_sysloop=sysloop_add(ixc_nat_sysloop_cb,NULL);

    if(NULL==nat_sysloop){
        STDERR("cannot add to sysloop\r\n");
        return -1;
    }

    rs=time_wheel_new(&nat_time_wheel,IXC_NAT_TIMEOUT*2/10,IXC_IO_WAIT_TIMEOUT,ixc_nat_timeout_cb,2048);

    if(0!=rs){
        sysloop_del(nat_sysloop);
        STDERR("cannot create time wheel\r\n");
        return -1;
    }

    rs=map_new(&m,7);
    if(rs){
        sysloop_del(nat_sysloop);
        time_wheel_release(&nat_time_wheel);
        STDERR("cannot init map\r\n");
        return -1;
    }
    nat.lan2wan=m;
    rs=map_new(&m,3);
    if(rs){
        sysloop_del(nat_sysloop);
        map_release(nat.lan2wan,NULL);
        time_wheel_release(&nat_time_wheel);
        STDERR("cannot init map\r\n");
        return -1;
    }
    nat.wan2lan=m;

    nat_is_initialized=1;

    return 0;
}

void ixc_nat_uninit(void)
{
    nat_is_initialized=0;

    return;
}

void ixc_nat_handle(struct ixc_mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    struct ixc_netif *wif=ixc_netif_get(IXC_NETIF_WAN);

    unsigned short frag_info,frag_off;
    int mf;

    if(!nat_is_initialized){
        ixc_mbuf_put(m);
        STDERR("please init nat\r\n");
        return;
    }

    // 未设置WAN口IP地址丢弃数据包
    if(!wif->isset_ip){
        ixc_mbuf_put(m);
        return;
    }

    frag_info=ntohs(header->frag_info);
    frag_off=frag_info & 0x1fff;
    mf=frag_info & 0x2000;

    if(mf!=0 || frag_off!=0) m=ixc_ipunfrag_add(m);
    if(NULL==m) return;


    IXC_MBUF_LOOP_TRACE(m);

    if(IXC_MBUF_FROM_LAN==m->from) ixc_nat_handle_from_lan(m);
    else ixc_nat_handle_from_wan(m);
}

unsigned int ixc_nat_sessions_num_get(void)
{
    return (nat.lan2wan)->key_tot_num;
}

int ixc_nat_set_id_range(unsigned short begin,unsigned short end)
{
    if(begin>=end) return -1;
    if(begin<1) return -1;

    nat.icmp_set.cur_id=begin;
    nat.icmp_set.id_min=begin;
    nat.icmp_set.id_max=end;

    nat.tcp_set.cur_id=begin;
    nat.tcp_set.id_min=begin;
    nat.tcp_set.id_max=end;

    nat.udp_set.cur_id=begin;
    nat.udp_set.id_min=begin;
    nat.udp_set.id_max=end;

    return 0;
}