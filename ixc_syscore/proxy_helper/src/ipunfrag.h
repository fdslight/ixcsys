#ifndef IPUNFRAG_H
#define IPUNFRAG_H

#include "mbuf.h"

#include "../../../pywind/clib/map.h"

#define IPUNFRAG_KEYSIZE 10
struct ipunfrag{
    struct map *m;
};

/// 具体包信息
struct ipunfrag_pktinfo{
    unsigned char data[0xffff];
    int tail;
    unsigned char key[IPUNFRAG_KEYSIZE];
};

int ipunfrag_init(void);
void ipunfrag_uninit(void);

struct mbuf *ipunfrag_add(struct mbuf *m);

#endif