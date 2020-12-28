#ifndef IP2SOCKS_TCP_H
#define IP2SOCKS_TCP_H

#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/netutils.h"


#define TCP_ACK 0x0010
#define TCP_RST 0x0040
#define TCP_SYN 0x0020
#define TCP_FIN 0x0001
/// 获取TCP标志
#define TCP_FLAGS(v,flags) (v & flags)

/// TCP缓冲区
struct tcp_buffer{
    // 数据开始位置
    unsigned short begin;
    // 数据结束位置
    unsigned short end;
    unsigned char data[0xffff];
};

/// TCP片段信息
struct tcp_data_seg{
    struct tcp_data_seg *next;
    // 该片段是否已经被使用
    int is_used;
    // TCP序列号
    unsigned short seq;
    // 缓冲区开始位置 
    unsigned short buf_begin;
    // 缓冲区结束位置
    unsigned short buf_end;
};

/// TCP会话信息
struct tcp_session{
    // 发送缓冲区
    struct tcp_buffer *sent_buffer;
    // 接收缓冲区
    struct tcp_buffer *recv_buffer;
    // 是否是IPv6地址
    int is_ipv6;
    // 会话ID
    unsigned char id[36];
    // 源地址
    unsigned char src_addr[16];
    // 目标地址
    unsigned char dst_addr[16];
    // 定时器
    // tcp会话状态
    int tcp_st;
    // 源端口号
    unsigned short sport;
    // 目的端口号
    unsigned short dport;
    // 序列号
    unsigned int seq;
    // 确认序列号
    unsigned int ack_seq;
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

#endif