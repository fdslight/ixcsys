#include<string.h>
#include<arpa/inet.h>

#include "tcp.h"
#include "debug.h"
#include "ip.h"
#include "ipv6.h"
#include "proxy_helper.h"

#include "../../../pywind/clib/netutils.h"

static struct tcp_sessions tcp_sessions;

static void tcp_session_del_cb(void *data)
{
    struct tcp_session *session=data;

    free(session);
}

static void tcp_session_timeout_cb(void *data)
{
    struct tcp_session *session=data;

    // 通过TCP状态对应处理
    switch(session->tcp_st){
        case TCP_ST_OK:
            break;
        case TCP_FIN_SND_WAIT:
            break;
    }
}

/// 发送TCP错误
static void tcp_send_rst(unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr)
{
}

static struct tcp_session *tcp_session_get(unsigned char *id,int is_ipv6)
{
    struct map *m=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;
    struct tcp_session *session;
    char is_found;

    session=map_find(m,(char *)id,&is_found);

    return session;
}

/// 发送TCP数据
static void tcp_send_data(struct tcp_session *session,unsigned short status,void *data,size_t size)
{
    struct netutil_ip6_ps_header *ps6_hdr;
    struct netutil_ip_ps_header *ps_hdr;
    struct netutil_tcphdr *tcphdr;
    unsigned short csum;
    struct mbuf *m=mbuf_get();

    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return;
    }

    m->begin=MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=MBUF_BEGIN+20+size;
    m->end=m->tail;

    tcphdr=(struct netutil_tcphdr *)(m->data+m->begin);
    bzero(tcphdr,20);

    // 计算检验和必须为2的倍数,如果长度为奇数,那么需要填充后一位为0补齐
    if(size % 2!=0) *(m->data+m->tail+1)='\0';
    
    // 源端口和目标端口要对调
    tcphdr->src_port=htons(session->dport);
    tcphdr->dst_port=htons(session->sport);

    // 发送本端的序列号
    tcphdr->seq_num=htonl(session->seq);
    // 对端序列号+1
    tcphdr->ack_num=htonl(session->peer_seq);

    tcphdr->header_len_and_flag=0x5000 | status;
    tcphdr->header_len_and_flag=htons(tcphdr->header_len_and_flag);
    tcphdr->win_size=htons(session->my_window_size);

    memcpy(m->data+m->begin+20,data,size);

    // TCP伪头部处理
    if(session->is_ipv6){
        ps6_hdr=(struct netutil_ip6_ps_header *)(m->data+m->begin-40);
        bzero(ps6_hdr,40);

        memcpy(ps6_hdr->src_addr,session->src_addr,16);
        memcpy(ps6_hdr->dst_addr,session->dst_addr,16);

        ps6_hdr->length=htons(40+size);
        ps6_hdr->next_header=6;

        csum=csum_calc((unsigned short *)(m->data+m->begin-40),m->end-m->begin+40);
    }else{
        ps_hdr=(struct netutil_ip_ps_header *)(m->data+m->begin-12);
        bzero(ps_hdr,12);

        memcpy(ps_hdr->src_addr,session->src_addr,4);
        memcpy(ps_hdr->dst_addr,session->dst_addr,4);

        ps_hdr->length=htons(20+size);
        ps_hdr->protocol=6;

        csum=csum_calc((unsigned short *)(m->data+m->begin-12),m->end-m->begin+12);
    }

    tcphdr->csum=csum;
    

    if(session->is_ipv6) ipv6_send(session->dst_addr,session->src_addr,6,m->data+m->begin,m->end-m->begin);
    else ip_send(session->dst_addr,session->src_addr,6,m->data+m->begin,m->end-m->begin);

    mbuf_put(m);
}

static void tcp_session_syn(const char *session_id,unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    struct tcp_session *session=NULL;
    struct map *map=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;
    char is_found;
    int rs;
    session=map_find(map,session_id,&is_found);

    if(NULL==session){
        session=malloc(sizeof(struct tcp_session));
        if(NULL==session){
            STDERR("cannot malloc tcp session\r\n");
            mbuf_put(m);
            return;
        }
        bzero(session,sizeof(struct tcp_session));
        rs=map_add(map,session_id,session);
        if(0!=rs){
            STDERR("cannot add to map for tcp syn\r\n");
            free(session);
            mbuf_put(m);
            return;
        }

        session->tm_node=tcp_timer_add(50,tcp_session_timeout_cb,session);

        if(NULL==session->tm_node){
            STDERR("cannot add to tcp timer\r\n");
            map_del(map,session_id,NULL);
            free(session);
            mbuf_put(m);
            return;
        }

        session->tcp_st=TCP_ST_SYN_SND;
    }

    session->is_ipv6=is_ipv6;

    if(is_ipv6) {
        memcpy(session->id,session_id,36);
        memcpy(session->src_addr,saddr,16);
        memcpy(session->dst_addr,daddr,16);

    }else{
        memcpy(session->id,session_id,12);
        memcpy(session->src_addr,saddr,4);
        memcpy(session->dst_addr,daddr,4);
    }

    session->sport=tcphdr->src_port;
    session->dport=tcphdr->dst_port;
    session->seq=0;
    session->my_window_size=TCP_DEFAULT_WIN_SIZE;

    session->peer_seq=tcphdr->seq_num+=1;
    session->peer_window_size=tcphdr->win_size;

    session->tcp_st=TCP_ST_SYN_SND;
    

    tcp_send_data(session,TCP_SYN | TCP_ACK,NULL,0);

    session->seq+=1;

    mbuf_put(m);
    return;
}

/// 发送缓冲区的数据
static void tcp_send_from_buf(struct tcp_session *session,struct netutil_tcphdr *tcphdr)
{
    // 根据窗口以及MTU计算出发送数据的大小
    int sent_size=0;
    // 总共发送的数据大小
    int tot_sent_size=0;
    struct mbuf *m=session->sent_seg_head;

    while(1){
        if(NULL==m) break;
        sent_size=m->tail-m->offset>1280?1280:m->tail-m->offset;
        tcp_send_data(session,TCP_ACK,m->data+m->offset,sent_size);
        m->offset+=sent_size;
        break;
    }

}

/// 发送确认处理
static void tcp_sent_ack_handle(struct tcp_session *session,struct netutil_tcphdr *tcphdr)
{
    struct mbuf *m=session->sent_seg_head,*t;
    int size,tot_size=0,ack_size,is_err=0;

    //if(tcphdr->ack_num<=session->seq) return;

    ack_size=tcphdr->ack_num-session->seq;

    while(NULL!=m){
        size=m->offset-m->begin;
        tot_size+=size;
        // 此处处理非法确认号情况
        if(tot_size>ack_size){
            is_err=1;
            break;
        }
        //DBG_FLAGS;
        if(0!=m->tail-m->offset) break;
        // 如果该mbuf已经被全部发送完毕,那么回收mbuf
        t=m->next;
        if(NULL==t) session->sent_seg_end=NULL;
        //DBG_FLAGS;
        mbuf_put(m);
        session->sent_seg_head=t;
        m=t;
    }

    if(!is_err) session->seq+=ack_size;
}

/// 函数返回0表示该数据包无效或者非法,否则表示该数据包有效
static int tcp_session_ack(struct tcp_session *session,struct netutil_tcphdr *tcphdr,struct mbuf *m)
{
    int payload_len=m->tail-m->offset;

    session->peer_window_size=tcphdr->win_size;

    if(TCP_ST_SYN_SND==session->tcp_st && session->peer_seq==tcphdr->seq_num){
        netpkt_tcp_connect_ev(session->id,session->src_addr,session->dst_addr,session->sport,session->dport,session->is_ipv6);
    }

    session->tcp_st=TCP_ST_OK;
    // 此处对发送的数据包进行确认并且发送发送缓冲区的数据
    if(tcphdr->seq_num==session->peer_seq && session->tcp_st==TCP_ST_OK){
        session->peer_seq=tcphdr->seq_num+payload_len;
        if(payload_len!=0) {
            netpkt_tcp_recv(session->id,tcphdr->win_size,session->is_ipv6,m->data+m->offset,payload_len);
        }
        tcp_sent_ack_handle(session,tcphdr);
        tcp_send_from_buf(session,tcphdr);
    }

    return 1;
}

static void tcp_session_fin(struct tcp_session *session,struct netutil_tcphdr *tcphdr,struct mbuf *m)
{
    session->peer_sent_closed=1;

    // 如果发送缓冲区不存在数据那么直接发送FIN并进入FIN wait状态
    if(NULL==session->sent_seg_head){
        session->tcp_st=TCP_FIN_SND_WAIT;
        session->seq+=1;
        tcp_send_data(session,TCP_ACK | TCP_FIN,NULL,0);
    }
}

static void tcp_session_rst(const char *session_id,unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    struct map *map=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;

    netpkt_tcp_close_ev((unsigned char *)session_id,is_ipv6);
    map_del(map,session_id,tcp_session_del_cb);

    mbuf_put(m);
}

static void tcp_session_handle(unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr,int is_ipv6,struct mbuf *m)
{
    char key[36];
    char is_found;

    struct tcp_session *session=NULL;
    struct map *map=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;
    int ack,rst,syn,fin,hdr_len,r;

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
    ack= hdr_and_flags & TCP_ACK;
    rst=hdr_and_flags & TCP_RST;
    syn=hdr_and_flags & TCP_SYN;
    fin=hdr_and_flags & TCP_FIN;

    // 不存在session那么就丢弃数据包
    if((ack || rst || fin) && NULL==session){
        mbuf_put(m);
        return;
    }
    // TCP SYN不能携带任何数据
    if(m->tail-m->offset!=hdr_len && syn){
        DBG("wrong TCP SYN protocol format\r\n");
        mbuf_put(m);
        return;
    }
    // 如果值都没有设置那么丢弃数据包
    if(!ack && !rst && !syn && !fin){
        // 会话存在那么就删除会话数据包
        if(NULL!=session){
            STDERR("client send wrong tcp packet\r\n");
        }
        DBG("wrong client TCP data format\r\n");
        mbuf_put(m);
        return;
    }

    tcphdr->src_port=sport;
    tcphdr->dst_port=dport;
    tcphdr->seq_num=seq;
    tcphdr->ack_num=ack_seq;
    tcphdr->win_size=ntohs(tcphdr->win_size);

    m->offset+=hdr_len;

    if(rst){
        tcp_session_rst(key,saddr,daddr,tcphdr,is_ipv6,m);
        return;
    }

    if(syn){
        tcp_session_syn(key,saddr,daddr,tcphdr,is_ipv6,m);
        return;
    }

    r=tcp_session_ack(session,tcphdr,m);
    if(fin && r) tcp_session_fin(session,tcphdr,m);
    
    // ack和fin的处理不自动回收mbuf
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
    struct tcp_session *session=tcp_session_get(session_id,is_ipv6);
    struct mbuf *mbuf;

    if(NULL==session) return -1;

    mbuf=mbuf_get();
    if(NULL==mbuf){
        STDERR("cannot get mbuf for send tcp data\r\n");
        return -2;
    }

    mbuf->begin=MBUF_BEGIN;
    mbuf->offset=MBUF_BEGIN;
    mbuf->tail=mbuf->begin+length;
    mbuf->end=mbuf->tail;
    mbuf->next=NULL;

    memcpy(mbuf->data+mbuf->begin,data,length);

    if(NULL==session->sent_seg_head){
        session->sent_seg_head=mbuf;
    }else{
        session->sent_seg_end->next=mbuf;
    }

    session->sent_seg_end=mbuf;

    return 0;
}

int tcp_close(unsigned char *session_id,int is_ipv6)
{
    return 0;
}

int tcp_window_set(unsigned char *session_id,int is_ipv6,unsigned short win_size)
{
    struct tcp_session *session;
    session=tcp_session_get(session_id,is_ipv6);

    if(NULL==session) return -1;

    session->my_window_size=win_size;

    return 0;
}

int tcp_send_reset(unsigned char *session_id,int is_ipv6)
{
    return 0;
}

inline
int tcp_have_sent_data(void)
{
    if(tcp_sessions.sent_buf_cnt) return 1;
    return 0;
}