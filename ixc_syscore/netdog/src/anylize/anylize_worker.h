#ifndef IXC_ANYLIZE_WORKER_H
#define IXC_ANYLIZE_WORKER_H

#include<pthread.h>
#include "../mbuf.h"

// 最大线程数目
#define IXC_WORKER_NUM_MAX 256

// 线程上下文环境
struct ixc_worker_context{
    // 需要回收的mbuf
    struct ixc_mbuf *recycle;
    struct ixc_mbuf *npkt;
    struct ixc_mbuf *npkt_last;
    pthread_t id;
    // 线程是否正在工作
    int is_working;
    // 当前线程索引
    int idx;
};

int ixc_anylize_worker_init(void);
int ixc_anylize_create_workers(int num);
void ixc_anylize_worker_uninit(void);

struct ixc_worker_context *ixc_anylize_worker_get(int seq);

#endif