#ifndef IXC_NAT_H
#define IXC_NAT_H

#include<time.h>

#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"

struct ixc_nat_id;

struct ixc_nat_session{
    struct ixc_nat_id *nat_id;
    struct time_data *tdata;
    // 会话更新时间
    time_t up_time;
    unsigned char addr[4];
    unsigned short lan_id;
    unsigned short wan_id;

    unsigned char lan_key[7];
    unsigned char _pad1[1];
    unsigned char wan_key[7];
    unsigned char _pad2[1];
    // 最小超时标记,如果设置了此标记,那么使用最小超时
    int min_timeout_flags;
    unsigned char protocol;
    // 引用计数
    unsigned char refcnt;
};

#define IXC_NAT_ID_MIN 10000
#define IXC_NAT_ID_MAX 60000

// NAT 超时时间
// 最小超时时间
#define IXC_NAT_MIN_TIMEOUT 10
// 标准超时时间
#define IXC_NAT_TIMEOUT 180

struct ixc_nat_id{
    struct ixc_nat_id *next;
    // 主机序ID
    unsigned short id;;
    // 网络序ID
    unsigned short net_id;
};

/// ID集合
struct ixc_nat_id_set{
    struct ixc_nat_id *head;
    unsigned short id_min;
    unsigned short id_max;
    unsigned short cur_id;
    char pad[2];
};

struct ixc_nat{
    // lan2wan的映射保存
    struct map *lan2wan;
    // wan2lan的保存
    struct map *wan2lan;
    struct ixc_nat_id_set icmp_set;
    struct ixc_nat_id_set tcp_set;
    struct ixc_nat_id_set udp_set;
};

#include "mbuf.h"

int ixc_nat_init(void);
void ixc_nat_uninit(void);

void ixc_nat_handle(struct ixc_mbuf *m);
int ixc_nat_enable(int status);

/// 获取nat会话数量
unsigned int ixc_nat_sessions_num_get(void);

/// 设置NAT地址范围
int ixc_nat_set_id_range(unsigned short begin,unsigned short end);

#endif