#ifndef PROXY_HELPER_H
#define PROXY_HELPER_H

#include "mbuf.h"

/// 发送网络数据包
int netpkt_send(struct mbuf *m,int is_ipv6);

/// 接收UDP数据包
int netpkt_udp_recv(unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_udplite,int is_ipv6,void *data,int size);

/// 处理TCP连接事件
int netpkt_tcp_connect_ev(unsigned char *id,unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_ipv6);
/// 处理TCP接收
int netpkt_tcp_recv(unsigned char *id,unsigned short win_size,int is_ipv6,void *data,int length);
/// 处理TCP关闭事件
int netpkt_tcp_close_ev(unsigned char *id,int is_ipv6);

#endif