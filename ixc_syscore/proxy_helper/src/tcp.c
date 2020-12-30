#include<string.h>
#include<arpa/inet.h>

#include "tcp.h"
#include "debug.h"

#include "../../../pywind/clib/netutils.h"

static struct tcp_sessions tcp_sessions;

static void tcp_session_del_cb(void *data)
{

}


static void tcp_session_syn(const char *session_id,unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    
}

static void tcp_session_ack(const char *session_id,unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    mbuf_put(m);
}

static void tcp_session_fin(const char *session_id,unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    mbuf_put(m);
}

static void tcp_session_rst(const char *session_id,unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    mbuf_put(m);
}

static void tcp_session_handle(unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    char key[36];
    char is_found;

    struct tcp_session *session=NULL;
    struct map *map=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;
    int ack,rst,syn,fin,hdr_len;
    int status[4],flags=0,error=0;

    unsigned short sport,dport,hdr_and_flags;
    unsigned int seq,ack_seq;

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

    sport=ntohs(tcphdr->src_port);
    dport=ntohs(tcphdr->dst_port);

    seq=ntohl(tcphdr->seq_num);
    ack_seq=ntohl(tcphdr->ack_num);

    hdr_and_flags=ntohs(tcphdr->header_len_and_flag);

    hdr_len=((hdr_and_flags & 0xf000) >> 12) * 4;
    ack=(hdr_and_flags & 0x0010) >> 4;
    rst=(hdr_and_flags & 0x0004) >> 2;
    syn=(hdr_and_flags & 0x0002) >> 1;
    fin=hdr_and_flags & 0x0001;

    // 不存在session那么就丢弃数据包
    if((ack || rst || fin) && NULL==session){
        mbuf_put(m);
        return;
    }

    // 如果值都没有设置那么丢弃数据包
    if(!ack && !rst && !syn && !fin){
        // 会话存在那么就删除会话数据包
        if(NULL!=session){
            STDERR("client send wrong tcp packet\r\n");
        }
        mbuf_put(m);
        return;
    }

    // 检查状态是否冲突
    status[0]=ack;
    status[1]=rst;
    status[2]=syn;
    status[3]=fin;

    for(int n=0;n<4;n++){
        if(status[n]) {
            flags=1;
            continue;
        }

        if(flags && status[n]) error=1;
    }

    // 处理协议故障
    if(error){
        mbuf_put(m);
        return;
    }

    tcphdr->src_port=sport;
    tcphdr->dst_port=dport;
    tcphdr->seq_num=seq;
    tcphdr->ack_num=ack_seq;
    tcphdr->win_size=ntohs(tcphdr->win_size);

    m->offset+=hdr_len;

    if(syn){
        tcp_session_syn(key,saddr,daddr,tcphdr,is_ipv6,m);
        return;
    }

    if(ack){
        tcp_session_ack(key,saddr,daddr,tcphdr,is_ipv6,m);
        return;
    }

    if(rst){
        tcp_session_rst(key,saddr,daddr,tcphdr,is_ipv6,m);
        return;
    }

    if(fin){
        tcp_session_fin(key,saddr,daddr,tcphdr,is_ipv6,m);
        return;
    }

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