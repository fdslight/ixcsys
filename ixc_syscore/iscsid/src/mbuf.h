#ifndef IXC_MBUF_H
#define IXC_MBUF_H

#include<sys/types.h>

#include "../../../pywind/clib/debug.h"

#define IXC_MBUF_LOOP_TRACE_MAX_NUM 32
#define IXC_MBUF_MAX 4096

struct ixc_mbuf{
    struct ixc_mbuf *next;
    void *priv_data;
#define IXC_MBUF_BEGIN 512
    int begin;
    // 偏移位置
    int offset;
    // 尾部
    int tail;
    // 循环跟踪,造成死循环那么给予警告
    int loop_trace;
    // 结束位置
#define IXC_MBUF_END 0xffff
    int end;
#define IXC_MBUF_DATA_MAX_SIZE 0x101ff
    unsigned char data[IXC_MBUF_DATA_MAX_SIZE];
};

/// 检查是否造成了死循环
#ifdef DEBUG
#define IXC_MBUF_LOOP_TRACE(M) \
if(M->loop_trace > IXC_MBUF_LOOP_TRACE_MAX_NUM){\
    STDERR("network packet endless loop\r\n");\
    ixc_mbuf_put(M);\
}
#else
#define IXC_MBUF_LOOP_TRACE(M)
#endif

int ixc_mbuf_init(size_t pre_alloc_num);
void ixc_mbuf_uninit(void);

struct ixc_mbuf *ixc_mbuf_get(void);
void ixc_mbuf_put(struct ixc_mbuf *m);
/// 克隆mbuf
struct ixc_mbuf *ixc_mbuf_clone(struct ixc_mbuf *m);

#endif