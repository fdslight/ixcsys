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

/// 发送TCP错误
static void tcp_send_rst(unsigned char *saddr,unsigned char *daddr,struct netutil_tcphdr *tcphdr)
{
    
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
    memcpy(m->data+m->begin+20,data,size);

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

    session->peer_seq=tcphdr->seq_num;
    session->peer_window_size=tcphdr->win_size;

    session->tcp_st=TCP_ST_SYN_SND;
    

    tcp_send_data(session,TCP_SYN | TCP_ACK,NULL,0);

    mbuf_put(m);
    return;
}

static void tcp_insert_to_recv_buf(struct tcp_session *session,struct netutil_tcphdr *tcphdr,struct mbuf *m)
{
    struct tcp_data_seg *p=NULL,*seg;
    int size=m->tail-m->offset;
    // 如果长度为0那么不插入tcp接收缓冲区
    if(0==size) return;

    seg=tcp_data_seg_get();
    if(NULL==seg){
        STDERR("cannot get struct tcp_data_seg\r\n");
        return;
    }
    if(NULL==session->recv_seg_head){
        seg->buf_begin=0;
        seg->buf_end=size;
        memcpy(session->recv_data+seg->buf_begin,m->data+m->offset,size);
        return;
    }

    // 查找合适的插入位置


    // 如果未找到合适的插入位置那么放弃
    if(NULL==p){
        tcp_data_seg_put(seg);
        return;
    }
}

/// 函数返回0表示该数据包无效或者非法,否则表示该数据包有效
static int tcp_session_ack(struct tcp_session *session,struct netutil_tcphdr *tcphdr,struct mbuf *m)
{
    int payload_len=m->tail-m->offset;
    struct tcp_data_seg *seg=session->recv_seg_head,*t;

    // 检查对端确认序列号是否超过已经发送的最大值,如果超过直接发送TCP RST
    if(tcphdr->ack_num>session->seq+1){
        return 0;
    }

    session->tcp_st=TCP_ST_OK;
    // 插入TCP数据包到接收缓冲区
    tcp_insert_to_recv_buf(session,tcphdr,m);

    if(tcphdr->seq_num>=session->peer_seq){
        session->peer_seq=tcphdr->seq_num;
        tcp_send_data(session,TCP_ACK,NULL,0);
    }

    return 1;
}

static void tcp_session_fin(struct tcp_session *session,struct netutil_tcphdr *tcphdr,struct mbuf *m)
{
    session->peer_sent_closed=1;

    tcp_send_data(session,TCP_ACK | TCP_FIN,NULL,0);
   
    session->tcp_st=TCP_FIN_SND_WAIT;

    // 如果发送缓冲区存在数据那么直接发送ACK
    if(NULL!=session->sent_seg_head){
        
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


int tcp_init(int data_seg_num)
{
    struct map *m;
    struct tcp_data_seg *seg;
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

    for(int n=0;n<data_seg_num;n++){
        seg=malloc(sizeof(struct tcp_data_seg));
        if(NULL==seg){
            STDERR("cannot pre malloc struct tcp_data_seg\r\n");
            tcp_uninit();
            return -1;
        }
        bzero(seg,sizeof(struct tcp_data_seg));
        seg->next=tcp_sessions.empty_head;
        tcp_sessions.empty_head=seg;
    }

    return 0;
}

void tcp_uninit(void)
{
    map_release(tcp_sessions.sessions6,tcp_session_del_cb);
    map_release(tcp_sessions.sessions,tcp_session_del_cb);
}

struct tcp_data_seg *tcp_data_seg_get(void)
{
    struct tcp_data_seg *seg=NULL;
    
    if(NULL!=tcp_sessions.empty_head){
        seg=tcp_sessions.empty_head;
        tcp_sessions.empty_head=seg->next;
    }else{
        seg=malloc(sizeof(struct tcp_data_seg));
        if(NULL==seg){
            STDERR("cannot malloc struct tcp_data_seg\r\n");
        }else{
            DBG("malloc struct tcp_data_seg\r\n");
            tcp_sessions.used_buf_info_num+=1;
        }
    }
    if(NULL!=seg) bzero(seg,sizeof(struct tcp_data_seg));

    return seg;
}

void tcp_data_seg_put(struct tcp_data_seg *seg)
{
    if(NULL==seg) return;
    if(tcp_sessions.used_buf_info_num>tcp_sessions.pre_alloc_buf_info_num){
        free(seg);
        tcp_sessions.used_buf_info_num-=1;
        return;
    }
    seg->next=NULL;
    tcp_sessions.empty_head=seg;
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