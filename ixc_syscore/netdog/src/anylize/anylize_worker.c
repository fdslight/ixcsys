#include <string.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

#include "anylize_worker.h"


int ixc_anylize_worker_init(void)
{
    return 0;
}

void ixc_anylize_worker_uninit(void)
{
}

void ixc_anylize_netpkt(struct ixc_mbuf *m)
{
    STDERR("hello,world\r\n");
    ixc_mbuf_put(m);
}