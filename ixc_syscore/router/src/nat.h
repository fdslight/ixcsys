#ifndef IXC_NAT_H
#define IXC_NAT_H

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

struct ixc_nat_session{
    unsigned char addr[4];
    unsigned short lan_id;
    unsigned short wan_id;
    unsigned char protocol;
    // 引用计数
    unsigned char refcnt;
};


#define IXC_NAT_BEGIN 10000
#define IXC_NAT_END 60000

struct ixc_nat_id{
    struct ixc_nat_id *next;
    unsigned short id;;
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
    struct ixc_nat_id_set udplite_set;
    struct ixc_nat_id_set sctp_set;
};

#include "mbuf.h"

int ixc_nat_init(void);
void ixc_nat_uninit(void);

void ixc_nat_handle(struct ixc_mbuf *m);

#endif