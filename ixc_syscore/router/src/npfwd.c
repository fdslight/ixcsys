#include<arpa/inet.h>
#include<unistd.h>
#include<string.h>
#include<errno.h>

#include "npfwd.h"
#include "router.h"
#include "ether.h"
#include "vswitch.h"
#include "ip.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"

static struct ixc_npfwd npfwd;
static struct ixc_npfwd_info npfwd_info[IXC_NPFWD_INFO_MAX];

static struct ixc_mbuf *npfwd_mbuf_first=NULL;
static struct ixc_mbuf *npfwd_mbuf_last=NULL;

static void ixc_npfwd_rx_data(int fd)
{
    struct ixc_mbuf *m;
    ssize_t recv_size;
    struct sockaddr from;
    socklen_t fromlen;
    struct ixc_npfwd_header *header;
    struct ixc_npfwd_info *info;
    struct ixc_netif *netif;

    for(int n=0;n<10;n++){
        m=ixc_mbuf_get();
        if(NULL==m){
            STDERR("cannot get mbuf\r\n");
            break;
        }
        recv_size=recvfrom(fd,m->data+IXC_MBUF_BEGIN,IXC_MBUF_DATA_MAX_SIZE-IXC_MBUF_BEGIN,0,&from,&fromlen);
        if(recv_size<0){
            ixc_mbuf_put(m);
            break;
        }

        // 检查是否满足最小长度要求
        if(fromlen<sizeof(struct ixc_npfwd_header)){
            ixc_mbuf_put(m);
            continue;
        }

        m->begin=IXC_MBUF_BEGIN;
        m->offset=IXC_MBUF_BEGIN;
        m->tail=IXC_MBUF_BEGIN+fromlen;
        m->end=m->tail;

        header=(struct ixc_npfwd_header *)(m->data+m->offset);
        if(header->flags>=IXC_NPFWD_INFO_MAX){
            ixc_mbuf_put(m);
            continue;
        }

        info=&(npfwd_info[header->flags]);

        // 如果未使用那么直接丢弃数据包
        if(!info->is_used){
            ixc_mbuf_put(m);
            continue;
        }
        
        // 验证key是否一致
        if(memcmp(header->key,info->key,16)){
            ixc_mbuf_put(m);
            continue;
        }

        // 找不到网卡直接丢弃数据包
        netif=ixc_netif_get(header->if_type);
        if(NULL==netif){
            ixc_mbuf_put(m);
            continue;
        }

        m->begin=m->offset=m->begin+20;

        m->netif=netif;

        switch(header->flags){
            case IXC_FLAG_ARP:
                ixc_ether_send2(m);
                break;
            case IXC_FLAG_DHCP_CLIENT:
                ixc_ether_send2(m);
                break;
            case IXC_FLAG_DHCP_SERVER:
                ixc_ether_send2(m);
                break;
            case IXC_FLAG_VSWITCH:
                break;
            case IXC_FLAG_SRC_FILTER:
                break;
            case IXC_FLAG_ROUTE_FWD:
                ixc_ip_send(m);
                break;
            default:
                ixc_mbuf_put(m);
                break;
        }
    }

}

static void ixc_npfwd_tx_data(void)
{
    struct ixc_mbuf *m=npfwd_mbuf_first,*t;
    struct ixc_npfwd_header *header;
    struct ixc_npfwd_info *info;
    struct sockaddr sent_addr;
    struct ev *ev;
    ssize_t sent_size;
    socklen_t tolen;

    while(1){
        if(NULL==m) break;

        header=(struct ixc_npfwd_header *)(m->data+m->offset);
        info=&(npfwd_info[header->flags]);

        // 如果转发已经关闭那么丢弃数据包
        if(!info->is_used){
            t=m->next;
            ixc_mbuf_put(m);
            m=t;
            continue;
        }

        // 检查key是否已经发生变更,发生变更那么丢弃数据包
        if(memcmp(info->key,header->key,16)){
            t=m->next;
            ixc_mbuf_put(m);
            m=t;
            continue;
        }

        m->begin+=20;
        m->offset+=20;

        sent_size=sendto(npfwd.fileno,m->data+m->offset,m->tail-m->offset,0,&sent_addr,tolen);
        if(sent_size<0){
            if(EAGAIN==errno){
                npfwd_mbuf_first=m;
            }else{
                // 此处避免发生错误堆积过多数据包导致内存被使用完毕
                t=m->next;
                ixc_mbuf_put(m);
                m=t;
                STDERR("error for send forward data\r\n");
            }
            break;
        }

        t=m->next;
        ixc_mbuf_put(m);
        m=t;
    }

    npfwd_mbuf_first=m;
    ev=ev_get(npfwd.ev_set,npfwd.fileno);

    if(NULL==npfwd_mbuf_first){
        npfwd_mbuf_last=NULL;
        ev_modify(npfwd.ev_set,ev,EV_WRITABLE,EV_CTL_DEL);
    }else{
        ev_modify(npfwd.ev_set,ev,EV_WRITABLE,EV_CTL_ADD);
    }
}

static int ixc_npfwd_readable_fn(struct ev *ev)
{
    ixc_npfwd_rx_data(ev->fileno);

    return 0;
}

static int ixc_npfwd_writable_fn(struct ev *ev)
{
    ixc_npfwd_tx_data();

    return 0;
}

static int ixc_npfwd_timeout_fn(struct ev *ev)
{
    return 0;
}

static int ixc_npfwd_del_fn(struct ev *ev)
{
    return 0;
}

int ixc_npfwd_init(struct ev_set *ev_set)
{
    int listenfd,rs;
    struct sockaddr_in in_addr;
    char buf[256];
    struct ev *ev;

    bzero(npfwd_info,sizeof(struct ixc_npfwd_info)*IXC_NPFWD_INFO_MAX);

    listenfd=socket(AF_INET,SOCK_DGRAM,0);

    if(listenfd<0){
        STDERR("cannot create socket fileno\r\n");
        return -1;
    }

    memset(&in_addr,'0',sizeof(struct sockaddr_in));

    in_addr.sin_family=AF_INET;

    memcpy(&(in_addr.sin_addr.s_addr),buf,4);
	in_addr.sin_port=htons(8964);

    inet_pton(AF_INET,"127.0.0.1",buf);
    rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr));

    if(rs<0){
        STDERR("cannot bind npfwd\r\n");
        close(listenfd);

        return -1;
    }

    rs=ev_setnonblocking(listenfd);
	if(rs<0){
		close(listenfd);
		STDERR("cannot set nonblocking\r\n");
		return -1;
	}

    npfwd.fileno=listenfd;
    npfwd.ev_set=ev_set;

    ev=ev_create(ev_set,listenfd);
    if(NULL==ev){
		close(listenfd);
		STDERR("cannot create event for fd %d\r\n",listenfd);
		return -1;
	}

    if(ev_timeout_set(ev_set,ev,10)<0){
		STDERR("cannot set timeout for fd %d\r\n",listenfd);
        return -1;
	}

	EV_INIT_SET(ev,ixc_npfwd_readable_fn,ixc_npfwd_writable_fn,ixc_npfwd_timeout_fn,ixc_npfwd_del_fn,&npfwd);
	rs=ev_modify(ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
		ev_delete(ev_set,ev);
		STDERR("cannot add to readablefor fd %d\r\n",listenfd);
		return -1;
	}

    return 0;
}

void ixc_npfwd_uninit(void)
{

}

int ixc_npfwd_send_raw(struct ixc_mbuf *m,unsigned char ipproto,unsigned char flags)
{
    struct ixc_npfwd_info *info;
    struct ixc_npfwd_header *header;

    if(NULL==m) return -1;
    // 检查索引是否合法
    if(flags>=IXC_NPFWD_INFO_MAX){
        ixc_mbuf_put(m);
        return -2;
    }

    info=&(npfwd_info[flags]);

    if(!info->is_used){
        ixc_mbuf_put(m);
        return -3;
    }

    header=(struct ixc_npfwd_header *)(m->data+m->offset-20);
    
    // 复制key
    memcpy(header->key,info->key,16);

    header->if_type=m->netif->type;
    header->ipproto=ipproto;
    header->flags=flags;

    if(NULL==npfwd_mbuf_first){
        npfwd_mbuf_first=m;
    }else{
        npfwd_mbuf_last->next=m;
    }
    npfwd_mbuf_last=m;

    // 立即发送数据
    ixc_npfwd_tx_data();

    return 0;
}

int ixc_npfwd_set_forward(unsigned char *key,unsigned short port,int flags)
{
    struct ixc_npfwd_info *info;

    if(port<1 || port>0xfffe){
        STDERR("wrong port number\r\n");
        return -1;
    }

    if(flags>=IXC_NPFWD_INFO_MAX){
        STDERR("wrong flags value\r\n");
        return -2;
    }

    info=&(npfwd_info[flags]);

    memcpy(info->key,key,16);
    // 直接转换为网络序,避免发送再多转换一次
    info->port=htons(port);

    return 0;
}