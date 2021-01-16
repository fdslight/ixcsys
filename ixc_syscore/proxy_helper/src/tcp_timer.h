#ifndef TCP_TIMER_H
#define TCP_TIMER_H

#include<sys/types.h>
struct tcp_timer_node;
typedef int (*tcp_timer_cb)(void *session);

/// TCP timer节点
struct tcp_timer_node{
    struct tcp_timer_node *prev;
    struct tcp_timer_node *next;
    // 指向的回调函数
    tcp_timer_cb fn;
    // 指向的TCP会话
    void *session;
    // 更新时间,单位是毫秒
    unsigned long long up_time;
    // 超时时间,单位是毫秒
    unsigned long long timeout;
    // 是否有效,如果为0表示该会话已经删除
    int is_valid;
};

struct tcp_timer{
};

#endif