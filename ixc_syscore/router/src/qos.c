#include<string.h>

#include "qos.h"

static struct ixc_qos ixc_qos;
static int ixc_qos_is_initialized=0;

int ixc_qos_init(void)
{

    bzero(&ixc_qos,sizeof(struct ixc_qos));
    ixc_qos_is_initialized=1;
    return 0;
}

void ixc_qos_uninit(void)
{
    ixc_qos_is_initialized=0;
}

void ixc_qos_add(struct ixc_mbuf *m)
{

}

void ixc_qos_pop(void)
{

}

int ixc_qos_have_data(void)
{
    if(ixc_qos.tot_pkt_num) return 1;

    return 0;
}

void ixc_qos_udp_udplite_first(int enable)
{
    
}