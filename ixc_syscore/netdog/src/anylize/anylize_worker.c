#include <string.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

#include "anylize_worker.h"
#include "../mbuf.h"

#include "../../../../pywind/clib/sysloop.h"
#include "../../../../pywind/clib/timer.h"

static struct sysloop *anylize_sysloop=NULL;
static struct time_wheel anylize_tw;

static void __ixc_anylize_sysloop_cb(struct sysloop *lp)
{
    time_wheel_handle(&anylize_tw);
}

static void __ixc_anylize_timeout_cb(void *data)
{

}

int ixc_anylize_worker_init(void)
{
    int rs;

    anylize_sysloop=sysloop_add(__ixc_anylize_sysloop_cb,NULL);

    if(NULL==anylize_sysloop){
        STDERR("cannot create sysloop\r\n");
        return -1;
    }

    rs=time_wheel_new(&anylize_tw,600,10,__ixc_anylize_timeout_cb,128);
    if(rs<0){
        STDERR("cannot create time wheel\r\n");
        return -1;
    }

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