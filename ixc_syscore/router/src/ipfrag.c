#include "ipfrag.h"

#include "../../../pywind/clib/debug.h"


static int ipfrag_is_initialized=0;

int ixc_ipfrag_init(void)
{

    return 0;
}

void ixc_ipfrag_uninit(void)
{

}

/// 对IP数据包进行分片
struct ixc_mbuf *ixc_ipfrag_frag(struct ixc_mbuf *m)
{
    if(!ipfrag_is_initialized){
        STDERR("please init ipfrag\r\n");
        return NULL;
    }

    return NULL;
}