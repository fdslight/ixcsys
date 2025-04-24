#ifndef IXC_IPUNFRAG_H
#define IXC_IPUNFRAG_H

// 最大分片会话数,超过这个会话数量那么就丢弃
#define IXC_IPUNFRAG_MAX_NUM 256


#if IXC_IPUNFRAG_MAX_NUM<64
#error IXC_IPUNFRAG MAX NUM must be 64 at least
#endif

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

struct ixc_ipunfrag{
    struct map *m;
};

int ixc_ipunfrag_init(void);
void ixc_ipunfrag_uninit(void);

/// 如果组包完成那么返回一个新的组合完成的mbuf
struct ixc_mbuf *ixc_ipunfrag_add(struct ixc_mbuf *m);

#endif