#include<string.h>
#include "ipunfrag.h"

static struct ipunfrag_set ipunfrag_set;
static int ipunfrag_is_initialized=0;

int ipunfrag_init(void)
{
    struct map *m;
    int rs;

    bzero(&ipunfrag_set,sizeof(struct ipunfrag_set));

    rs=map_new(&m,IPUNFRAG_KEYSIZE);
    if(0!=rs) return -1;

    ipunfrag_is_initialized=1;

    return 0;
}

void ipunfrag_uninit(void)
{

}

int ipunfrag_add(struct mbuf *m)
{
    return 0;
}

void *ipunfrag_get(void)
{

}