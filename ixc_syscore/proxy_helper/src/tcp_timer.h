#ifndef TCP_TIMER_H
#define TCP_TIMER_H

#include<sys/types.h>

#include "../../../pywind/clib/sysloop.h"

struct tcp_timer_node;
typedef void (*tcp_timer_cb_t)(void *data);
typedef unsigned long long tcp_time_t;

struct tcp_timer_tick;

/// TCP timer节点
struct tcp_timer_node{
    struct tcp_timer_node *prev;
    struct tcp_timer_node *next;
    // 所指向的tick
    struct tcp_timer_tick *tick;
    // 指向的回调函数
    tcp_timer_cb_t fn;
    // 指向的TCP会话
    void *data;
    // 是否有效,如果为0表示该会话已经删除
    int is_valid;
};

/// TCP timer tick
struct tcp_timer_tick{
    struct tcp_timer_tick *next;
    struct tcp_timer_node *head;
    // 对应的索引号
    int idx_no;
};

struct tcp_timer{
    struct tcp_timer_tick *next;
    struct tcp_timer_tick *tick_head;
    // tick索引
    struct tcp_timer_tick **tick_idx;
    struct sysloop *loop;
    // 更新时间
    time_t up_time;
    time_t tick_timeout;
    int tick_num;
};

/// 
// wheel_max表示最大超时,单位是秒
// tick_timeout表示单个tick的超时时间,单位是毫秒
int tcp_timer_init(time_t wheel_max,time_t tick_timeout);
void tcp_timer_uninit(void);

struct tcp_timer_node *tcp_timer_add(time_t timeout_ms,tcp_timer_cb_t fn,void *data);
void tcp_timer_update(struct tcp_timer_node *node,time_t timeout_ms);

void tcp_timer_del(struct tcp_timer_node *node);
void tcp_timer_do(void);

#endif