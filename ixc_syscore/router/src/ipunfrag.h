#ifndef IXC_IPUNFRAG_H
#define IXC_IPUNFRAG_H

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

struct ixc_ipunfrag{
    struct map *m;
};

int ixc_ipunfrag_init(void);
void ixc_ipunfrag_uninit(void);

struct ixc_mbuf *ixc_ipungrag_get(void);
int ixc_ipunfrag_add(struct ixc_mbuf *m);


#endif