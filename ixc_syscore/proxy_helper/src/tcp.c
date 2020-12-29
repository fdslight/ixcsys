#include<string.h>

#include "tcp.h"
#include "debug.h"

#include "../../../pywind/clib/netutils.h"

static struct tcp_sessions tcp_sessions;

static void tcp_session_del_cb(void *data)
{

}

static void tcp_session_handle(unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    char key[36];
    char is_found;

    struct tcp_session *session=NULL;
    struct map *map=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;

    if(is_ipv6){
        memcpy(key,saddr,16);
        memcpy(key+16,daddr,16);
        memcpy(key+32,&(tcphdr->src_port),2);
        memcpy(key+34,&(tcphdr->dst_port),2);
    }else{
        memcpy(key,saddr,4);
        memcpy(key,daddr,4);
        memcpy(key+8,&(tcphdr->src_port),2);
        memcpy(key+10,&(tcphdr->dst_port),2);
    }

    session=map_find(map,key,&is_found);

    mbuf_put(m);
}

static void tcp_handle_for_v4(struct mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int hdr_len=(header->ver_and_ihl & 0x0f) * 4;
    struct netutil_tcphdr *tcphdr=(struct netutil_tcphdr *)(m->data+m->offset+hdr_len);

    m->offset=m->offset+hdr_len;
    tcp_session_handle(header->src_addr,header->dst_addr,tcphdr,0,m);
}

static void tcp_handle_for_v6(struct mbuf *m)
{
    struct netutil_ip6hdr *header=(struct netutil_ip6hdr *)(m->data+m->offset);
    struct netutil_tcphdr *tcphdr=(struct netutil_tcphdr *)(m->data+m->offset+40);

    m->offset=m->offset+40;
    tcp_session_handle(header->src_addr,header->dst_addr,tcphdr,1,m);
}

int tcp_init(void)
{
    struct map *m;
    int rs;

    bzero(&tcp_sessions,sizeof(struct tcp_sessions));

    rs=map_new(&m,36);
    if(0!=rs){
        STDERR("cannot create map for TCPv6\r\n");
        return -1;
    }
    tcp_sessions.sessions6=m;

    rs=map_new(&m,12);
    if(0!=rs){
        map_release(tcp_sessions.sessions6,NULL);
        STDERR("cannot create map for TCP\r\n");
        return -1;
    }
    tcp_sessions.sessions=m;

    return 0;
}

void tcp_uninit(void)
{
    map_release(tcp_sessions.sessions6,tcp_session_del_cb);
    map_release(tcp_sessions.sessions,tcp_session_del_cb);
}

void tcp_handle(struct mbuf *m,int is_ipv6)
{
    if(is_ipv6) tcp_handle_for_v6(m);
    else tcp_handle_for_v4(m);
}

int tcp_send(unsigned char *session_id,void *data,int length,int is_ipv6)
{
    return 0;
}

int tcp_close(unsigned char *session_id,int is_ipv6)
{
    return 0;
}

int tcp_window_set(unsigned char *session_id,int is_ipv6,unsigned short win_size)
{
    struct map *m=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;
    struct tcp_session *session;
    char is_found;

    session=map_find(m,(char *)session_id,&is_found);
    if(!is_found) return -1;
    session->my_window_size=win_size;

    return 0;
}

int tcp_send_reset(unsigned char *session_id,int is_ipv6)
{
    return 0;
}