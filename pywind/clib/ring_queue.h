/// 实现环形队列
#ifndef IXC_RING_QUEUE_H
#define IXC_RING_QUEUE_H

struct ixc_rq_node;

struct ixc_rq{
    struct ixc_rq_node *nodes;
    int node_num;

    int consumer_pos;
    int producer_pos;

};

struct ixc_rq_node{
    void *data_ptr;
    int is_used;
};

int ixc_rq_create(struct ixc_rq *rq,unsigned short num);
void ixc_rq_delete(struct ixc_rq *rq);

int ixc_rq_push(struct ixc_rq *rq,void *data_ptr);
int ixc_rq_pop(struct ixc_rq *rq,void **data);

#endif