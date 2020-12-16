#ifndef IP2SOCKS_TCP_H
#define IP2SOCKS_TCP_H


#define TCP_ACK 0x0010
#define TCP_RST 0x0040
#define TCP_SYN 0x0020
#define TCP_FIN 0x0001
/// 获取TCP标志
#define TCP_FLAGS(v,flags) (v & flags)

/// TCP缓冲区
struct tcp_buffer{
    // 当前块索引
    int cur_blk_idx;
    // 已经发送的TCP块大小
#define TCP_BLK_NUM 256
    int blk_size[TCP_BLK_NUM];
    // 数据开始位置
    unsigned short begin;
    // 数据结束位置
    unsigned short end;
};

/// TCP会话信息
struct tcp_session{
    // 是否是IPv6地址
    int is_ipv6;
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
    unsigned short window_size;
};

#endif