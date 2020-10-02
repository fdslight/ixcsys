#ifndef IXC_NAT_H
#define IXC_NAT_H

#include<time.h>

#include "mbuf.h"

#include "../../../pywind/clib/map.h"
#include "../../../pywind/clib/timer.h"

struct ixc_nat_id;

struct ixc_nat_session{
    struct ixc_nat_id *nat_id;
    // 会话更新时间
    time_t up_time;
    unsigned char addr[4];
    unsigned short lan_id;
    unsigned short wan_id;
    unsigned char protocol;
    // 引用计数
    unsigned char refcnt;
};


#define IXC_NAT_ID_MIN 10000
#define IXC_NAT_ID_MAX 60000

/// NAT PASS即不执行NAT操作,而是直接PASS
#define IXC_NAT_TYPE_PASS 0
/// CONE NAT 模式
#define IXC_NAT_TYPE_CONE 1

// NAT 超时时间
#define IXC_NAT_TIMEOUT 300

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
    char pad[6];
    unsigned short cur_id;
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
int ixc_nat_enable(int status,int type);

#endif