#ifndef IXC_QOS_H
#define IXC_QOS_H

#include "mbuf.h"

struct ixc_qos_slot{
    struct ixc_qos_slot *next;
    int slot;
};

#define IXC_QOS_SLOT_NUM 1024

struct ixc_qos{
    struct ixc_mbuf *mbuf_slots_head[IXC_QOS_SLOT_NUM];
    struct ixc_mbuf *mbuf_slots_end[IXC_QOS_SLOT_NUM];

    struct ixc_qos_slot *empty_slot_head;
    struct ixc_qos_slot *used_slots_head;
    // 当前已有的包数量
    unsigned int tot_pkt_num;
    int udp_udplite_first;
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

/// 设置为UDP和UDPLite优先,调用此函数之后那么UDP和UDPLite直接被发送而不被QOS
/// 开启之后可减少语音和游戏等需要UDP和UDPLite场景的延迟
void ixc_qos_udp_udplite_first(int enable);

#endif