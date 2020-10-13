#ifndef IXC_LCP_H
#define IXC_LCP_H

#include "mbuf.h"

struct ixc_lcp{
    unsigned int magic_num;
    unsigned char _id;
};

#pragma pack(push)
#pragma pack(1)

/// LCP code选项
#define IXC_LCP_CFG_REQ 1
#define IXC_LCP_CFG_ACK 2
#define IXC_LCP_CFG_NAK 3
#define IXC_LCP_CFG_REJECT 4
#define IXC_LCP_TERM_REQ 5
#define IXC_LCP_TERM_ACK 6
#define IXC_LCP_CODE_REJECT 7
#define IXC_LCP_PROTO_REJECT 8
#define IXC_LCP_ECHO_REQ 9
#define IXC_LCP_ECHO_REPLY 10
#define IXC_LCP_DISCARD_REQ 11

/// LCP配置头部
struct ixc_lcp_cfg_header{
    unsigned char code;
    unsigned char id;
    unsigned short length;
};

/// LCP配置选项头部
struct ixc_lcp_opt_header{
    unsigned char type;
    unsigned char length;
};


#define IXC_LCP_OPT_TYPE_RESERVED 0
#define IXC_LCP_OPT_TYPE_MAX_RECV_UNIT 1
#define IXC_LCP_OPT_TYPE_AUTH_PROTO 3
#define IXC_LCP_OPT_TYPE_QUA_PROTO 4
#define IXC_LCP_OPT_TYPE_MAGIC_NUM 5
#define IXC_LCP_OPT_TYPE_PROTO_COMP 7
#define IXC_LCP_OPT_TYPE_ADDR_CTL_COMP 8

/// LCP配置选项
struct ixc_lcp_opt{
    struct ixc_lcp_opt *next;
    unsigned char type;
    unsigned char length;
    unsigned char data[512];
};

#pragma pack(pop)

void ixc_lcp_handle(struct ixc_mbuf *m);
void ixc_lcp_request_send(void);


#endif