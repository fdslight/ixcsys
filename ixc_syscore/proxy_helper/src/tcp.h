#ifndef IP2SOCKS_TCP_H
#define IP2SOCKS_TCP_H

#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/netutils.h"

#define TCP_ACK 0x0010
#define TCP_RST 0x0004
#define TCP_SYN 0x0002
#define TCP_FIN 0x0001

/// TCP状态
enum{
    // SYN已经发送
    TCP_ST_SYN_SND=1,
    TCP_ST_OK,
    // 发送FIN发送等待
    TCP_FIN_SND_WAIT,
    // TCP发送关闭
    TCP_FIN_SND
};

/// 获取TCP标志
#define TCP_FLAGS(v,flags) (v & flags)

/// TCP会话信息
struct tcp_session{
    // 发送段信息
    struct mbuf *sent_seg_head;
    // 接收到的数据
    unsigned char recv_data[0xffff];
    // 发送的数据
    unsigned char sent_data[0xffff];

    // 是否是IPv6地址
    int is_ipv6;
    // 会话ID
    unsigned char id[36];
    // 源地址
    unsigned char src_addr[16];
    // 目标地址
    unsigned char dst_addr[16];
    // 对端发送是否关闭
    int peer_sent_closed;
    // 定时器
    // tcp会话状态
    int tcp_st;
    // 对端TCP mss
    int peer_mss;
    // 本端TCP mss
    int my_mss;
    // 源端口号
    unsigned short sport;
    // 目的端口号
    unsigned short dport;
    // 序列号
    unsigned int seq;
    // 确认序列号
    unsigned int ack_seq;
    // 已经收到的对端最小可用连续序列号
    unsigned int peer_seq;
    // 窗口大小
#define TCP_DEFAULT_WIN_SIZE 512
    unsigned short my_window_size;
    // 对端窗口大小
    unsigned short peer_window_size;
    
};

struct tcp_sessions{
    // IPv4 TCP会话
    struct map *sessions;
    // IPv6 TCP会话
    struct map *sessions6;
    // 发送缓冲计数器,如果为0表示没有任何数据可以需要被发送
    unsigned long long sent_buf_cnt;
};

int tcp_init(void);
void tcp_uninit(void);

void tcp_handle(struct mbuf *m,int is_ipv6);

/// 发送TCP数据包
int tcp_send(unsigned char *session_id,void *data,int length,int is_ipv6);
/// 关闭TCP连接
int tcp_close(unsigned char *session_id,int is_ipv6);
/// 窗口大小设置
int tcp_window_set(unsigned char *session_id,int is_ipv6,unsigned short win_size);
/// 发送TCP RST报文
int tcp_send_reset(unsigned char *session_id,int is_ipv6);
/// 是否还有数据等待发送
int tcp_have_sent_data(void);

#endif