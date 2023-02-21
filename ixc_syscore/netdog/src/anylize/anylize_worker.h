#ifndef IXC_ANYLIZE_WORKER_H
#define IXC_ANYLIZE_WORKER_H

#include "../mbuf.h"

#define IXC_ANYLIZE_CTX_PUBLIC \
unsigned long long refcnt;\
unsigned long long tx_traffic;\
unsigned long long rx_traffic;\
unsigned long long sec_time;\
unsigned long long usec_time;\
unsigned long long action;

/// 应用层句柄
struct ixc_anylize_ctx_app{
    char data[8192];
};

/// 传输层句柄
struct ixc_anylize_ctx_trans{
    struct ixc_anylize_ctx_app *next_layer;
    unsigned short src_port_begin;
    unsigned short src_port_end;
    unsigned short dst_port_begin;
    unsigned short dst_port_end;

    IXC_ANYLIZE_CTX_PUBLIC;
};

/// 网络层句柄
struct ixc_anylize_ctx_net{
    struct ixc_anylize_ctx_trans *next_layer;

    unsigned char src_addr[16];
    unsigned char dst_addr[16];
    int is_ipv6;
    unsigned char ipproto;
    char pad[3];
    IXC_ANYLIZE_CTX_PUBLIC;
};

/// 链路层句柄
struct ixc_anylize_ctx_link{
    struct anylize_ctx_net *next_layer;

    unsigned char src_hwaddr[6];
    unsigned char pad[2];
    unsigned char dst_hwaddr[6];
    unsigned short link_proto;

    IXC_ANYLIZE_CTX_PUBLIC;
    
};

int ixc_anylize_worker_init(void);
void ixc_anylize_worker_uninit(void);
void ixc_anylize_netpkt(struct ixc_mbuf *m);

#endif