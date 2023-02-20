#ifndef IXC_ANYLIZE_WORKER_H
#define IXC_ANYLIZE_WORKER_H

#include<pthread.h>
#include "../mbuf.h"

// 最大线程数目
#define IXC_WORKER_NUM_MAX 256

struct ixc_worker_mbuf_ring{
    struct ixc_mbuf *next;
    int is_used;
    int pad[4];
};

// 线程上下文环境
struct ixc_worker_context{
    struct ixc_worker_mbuf_ring *ring;
    // ring 最后一个有数据的位置
    struct ixc_worker_mbuf_ring *ring_data_last;
#define IXC_WORKER_MBUF_RING_SIZE 128
    struct ixc_worker_mbuf_ring ring_data[IXC_WORKER_MBUF_RING_SIZE];
    pthread_t id;
    // 线程是否正在工作
    int is_working;
    // 当前线程索引
    int idx;
};

#if(IXC_WORKER_MBUF_RING_SIZE < 8)
#error the value of IXC_WORKER_MBUF_RING_SIZE is at last 8
#endif

int ixc_anylize_worker_init(void);
int ixc_anylize_create_workers(int num);
void ixc_anylize_worker_uninit(void);

struct ixc_worker_context *ixc_anylize_worker_get(int seq);

#endif