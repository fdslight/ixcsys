#include<sys/time.h>
#include<string.h>

#include "tcp_timer.h"
#include "debug.h"

static struct tcp_timer tcp_timer;

/// 根据超时获取对应的tick
static struct tcp_timer_tick *tcp_timer_get_tick(time_t timeout_ms)
{
    int tot=timeout_ms / tcp_timer.tick_timeout,r=timeout_ms % tcp_timer.tick_timeout;
    struct tcp_timer_tick *result=NULL;

    if(r>0) tot+=1;
    if(tot>0) tot-=1;

    result=tcp_timer.tick_idx[tot];

    return result;
}

int tcp_timer_init(time_t wheel_max,time_t tick_timeout)
{
    int tot=wheel_max * 1000 / tick_timeout;
    struct tcp_timer_tick *tick,*last=NULL;

    if(tot<1){
        STDERR("wrong argument value\r\n");
        return -1;
    }

    bzero(&tcp_timer,sizeof(struct tcp_timer));

    tcp_timer.tick_idx=malloc(sizeof(NULL)*(tot+1));
    if(NULL==tcp_timer.tick_idx){
        STDERR("no memory for tick index\r\n");
        return -1;
    }

    // 这里多加1避免索引溢出
    bzero(tcp_timer.tick_idx,sizeof(NULL) * (tot+1));

    for(int n=0;n<tot;n++){
        tick=malloc(sizeof(struct tcp_timer_tick));
        if(NULL==tick){
            tcp_timer_uninit();
            STDERR("no memory for struct tcp_timer_tick\r\n");
            return -1;
        }
        bzero(tick,sizeof(struct tcp_timer_tick));
        if(NULL==tcp_timer.tick_head) {
            tcp_timer.tick_head=tick;
        }else{
            last->next=tick;
        }
        last=tick;
        tcp_timer.tick_idx[n]=tick;
        tick->idx_no=n;
    }

    last->next=tcp_timer.tick_head;
    tcp_timer.up_time=time(NULL);
    tcp_timer.tick_timeout=tick_timeout;
    tcp_timer.tick_num=tot;

    return 0;
}

void tcp_timer_uninit(void)
{
    struct tcp_timer_tick *tick,*t_tick;
    struct tcp_timer_node *node,*t_node;

    for(int i=0;i<tcp_timer.tick_num;i++){
        tick=tcp_timer.tick_idx[i];
        
        node=tick->head;
        while(NULL!=node){
            t_node=node->next;
            free(node);
            node=t_node;
        }
        t_tick=tick->next;
        tick=t_tick;
    }

    free(tcp_timer.tick_idx);
}

struct tcp_timer_node *tcp_timer_add(time_t timeout_ms,tcp_timer_cb_t fn,void *data)
{
    struct tcp_timer_node *node;
    struct tcp_timer_tick *tick;

    node=malloc(sizeof(struct tcp_timer_node));

    if(NULL==node){
        STDERR("no memory for struct tcp_timer_add\r\n");
        return NULL;
    }

    bzero(node,sizeof(struct tcp_timer_node));

    tick=tcp_timer_get_tick(timeout_ms);

    if(NULL!=tick->head) tick->head->prev=node;

    tick->head=node;

    node->is_valid=1;
    node->fn=fn;
    node->tick=tick;
    node->data=data;

    return node;
}

void tcp_timer_update(struct tcp_timer_node *node,time_t timeout_ms)
{
    struct tcp_timer_tick *tick=node->tick;

    if(NULL==node->prev) tick->head=node->next;
    else node->prev->next=node->next;

    node->next=NULL;
    node->prev=NULL;
    node->timeout_flags=0;

    tick=tcp_timer_get_tick(timeout_ms);
    
    if(NULL!=tick->head){
        tick->head->prev=node;
        node->next=tick->head;
    }
    tick->head=node;
}

void tcp_timer_del(struct tcp_timer_node *node)
{
    // 如果设置了超时标志,那么释放内存
    if(node->timeout_flags){
        free(node);
    }else{
        // 如果未超时那么设置为无效
        node->is_valid=1;
    }
}

void tcp_timer_do(void)
{
    struct timeval tv;
    int ms,tot;
    struct tcp_timer_tick *tick=tcp_timer.tick_head;
    struct tcp_timer_node *node,*t_node;

    gettimeofday(&tv,NULL);

    ms=(tv.tv_sec-tcp_timer.up_time)*1000+tv.tv_usec/1000;
    tot=ms / tcp_timer.tick_timeout;

    //DBG("%d\r\n",tot);

    for(int n=0;n<tot;n++){
        node=tick->head;
        while(NULL!=node){
            if(!node->is_valid){
                t_node=node->next;
                free(node);
                node=t_node;
            }else{
                node->timeout_flags=1;
                // 这里可能在回调函数出现删除node情况,此处需要提前指向下一个node
                t_node=node->next;
                node->fn(node->data);
                node=t_node;
            }
        }
        //DBG_FLAGS;
        // 清空node head,注意回收内存
        tick->head=NULL;
        tick=tick->next;
    }

    tcp_timer.tick_head=tick;
    tcp_timer.up_time=time(NULL);
 
}

