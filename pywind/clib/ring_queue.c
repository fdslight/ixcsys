#include<stdlib.h>
#include<string.h>

#include "ring_queue.h"

int ixc_rq_create(struct ixc_rq *rq,unsigned short num)
{
    struct ixc_rq_node *nodes;

    bzero(rq,sizeof(struct ixc_rq));

    if(num < 1) return -1;

    nodes=malloc(sizeof(struct ixc_rq_node)*num);
    
    bzero(nodes,sizeof(struct ixc_rq_node)*num);

    if(NULL==nodes){
        return -1;
    }

    rq->nodes=nodes;
    rq->node_num=num;

    return 0;

}

void ixc_rq_delete(struct ixc_rq *rq)
{
    free(rq->nodes);
}

int ixc_rq_push(struct ixc_rq *rq,void *data_ptr)
{
    struct ixc_rq_node *node;
    int slot=rq->producer_pos;
    node=&(rq->nodes[slot]);

    if(node->is_used){
        slot+=1;
        if(slot==rq->node_num) slot=0;
        node=&(rq->nodes[slot]);
        if(node->is_used) return -1;
    }
    
    rq->producer_pos=slot;
    node->data_ptr=data_ptr;
    // 这里使用标记最后赋值,避免多线程问题
    node->is_used=1;

    return 0;
}

int ixc_rq_pop(struct ixc_rq *rq,void **data)
{
    int slot=rq->consumer_pos;
    struct ixc_rq_node *node;

    *data=NULL;
    node=&(rq->nodes[slot]);

    if(!node->is_used) return -1;
    
    *data=node->data_ptr;
    node->is_used=0;

    if(slot!=rq->producer_pos){
        slot+=1;
    }

    if(slot==rq->node_num) slot=0;

    return 0;
}