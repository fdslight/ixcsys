#ifndef IXC_ANYLIZE_WORKER_H
#define IXC_ANYLIZE_WORKER_H

#define IXC_ANYLIZE_WORKER_LOCK_SYS_MSG 0
#define IXC_ANYLIZE_WORKER_LOCK_NETPKT 1

#include<pthread.h>
#include "../mbuf.h"

// 最大线程数目
#define IXC_WORKER_NUM_MAX 256
// 线程上下文环境
struct ixc_worker_context{
    struct ixc_mbuf *npkt_first;
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

// 获取锁
int ixc_anylize_worker_lock_get(int lock_flags);
// 释放锁
void ixc_anylize_worker_unlock(int lock_flags);

#endif