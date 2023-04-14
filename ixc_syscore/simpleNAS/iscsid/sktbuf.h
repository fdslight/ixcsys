#ifndef IXC_SKTBUF_H
#define IXC_SKTBUF_H

#include<sys/types.h>

#define IXC_SKTBUF_MAX 128

struct ixc_sktbuf{
    struct ixc_sktbuf *next;
    // 开始位置
#define IXC_MBUF_BEGIN 512
    int begin;
    // 偏移位置
    int offset;
    // 尾部
    int tail;
#define IXC_MBUF_END 0xffff
    int end;
#define IXC_MBUF_DATA_MAX_SIZE 0x101ff
    unsigned char data[IXC_MBUF_DATA_MAX_SIZE];
};


int ixc_sktbuf_init(size_t pre_alloc_num);
void ixc_sktbuf_uninit(void);

struct ixc_sktbuf *ixc_sktbuf_get(void);
void ixc_sktbuf_put(struct ixc_sktbuf *m);
/// 克隆sktbuf
struct ixc_sktbuf *ixc_sktbuf_clone(struct ixc_sktbuf *m);

#endif