#ifndef IXC_QOS_H
#define IXC_QOS_H

#include "mbuf.h"

struct ixc_qos_slot{
    struct ixc_mbuf *mbuf_first;
    struct ixc_mbuf *mbuf_last;

    struct ixc_qos_slot *next;

    int slot;
    int is_used;
};

#define IXC_QOS_SLOT_NUM 32768

struct ixc_qos{
    struct ixc_qos_slot *slot_objs[IXC_QOS_SLOT_NUM];
    struct ixc_qos_slot *slot_head;
    unsigned char tunnel_addr[16];
    int qos_mpkt_first_size;
    int tunnel_is_ipv6;
    int tunnel_isset;
};


int ixc_qos_init(void);
void ixc_qos_uninit(void);

/// 把流量加入到QOS槽中
void ixc_qos_add(struct ixc_mbuf *m);

/// 自动弹出槽中的数据
void ixc_qos_pop(void);

/// 检查QOS中是否还有数据未被发送
// 如果已经发送完毕那么返回0,否则返回1
int ixc_qos_have_data(void);

/// 设置隧道地址优先
int ixc_qos_tunnel_addr_first_set(unsigned char *addr,int is_ipv6);
/// 取消隧道地址优先
void ixc_qos_tunnel_addr_first_unset(void);

/// 设置小包优先策略
int ixc_qos_mpkt_first_set(int size);

#endif