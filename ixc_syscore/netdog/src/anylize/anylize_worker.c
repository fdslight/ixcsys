#include <string.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

#include "anylize_worker.h"

static struct ixc_worker_context *workers[IXC_WORKER_NUM_MAX];

__thread int worker_index = 0;

static void ixc_anylize_netpkt(void)
{
    struct ixc_worker_context *ctx = workers[worker_index];
    struct ixc_mbuf *m=ctx->npkt,*t;
    int cnt = 0;

    ctx->recycle = NULL;
    
    while(NULL!=m){
        cnt++;
        t=m->next;
        m->next = NULL;

        ixc_mbuf_put(m);
        m=t;

        if (cnt > 8){
            ixc_mbuf_puts(ctx->recycle);
            ctx->recycle = NULL;
            cnt = 0;
        }
        STDERR("ZVCS\r\n");
    }

    ctx->npkt=NULL;
    ctx->npkt_last=NULL;
    ctx->is_working = 0;

    STDERR("handle data\r\n");
}

static void ixc_anylize_sig_handle(int signum)
{
    if (SIGUSR1 != signum)
        return;
}

static void ixc_anylize_worker_loop(struct ixc_worker_context *context)
{
    struct ixc_worker_context *ctx=workers[worker_index];

    while (1)
    {
        if(ctx->is_working){
            STDERR("ZZZAAA\r\n");
            ixc_anylize_netpkt();
        }else{
           
        }
        usleep(1);
    }
}

static void *ixc_anylize_worker_start(void *thread_context)
{
    struct ixc_worker_context *context = thread_context;

    sigset_t mask;

    worker_index = context->idx;
    // 屏蔽SIGINT信号
    sigemptyset(&mask);
    sigaddset(&mask, SIGINT);
    pthread_sigmask(SIG_SETMASK, &mask, NULL);

    context->id = pthread_self();
    ixc_anylize_worker_loop(context);

    return NULL;
}

int ixc_anylize_worker_init(void)
{
    bzero(workers, sizeof(NULL) * IXC_WORKER_NUM_MAX);

    signal(SIGUSR1, ixc_anylize_sig_handle);

    return 0;
}

int ixc_anylize_create_workers(int num)
{
    struct ixc_worker_context *context = NULL;
    int rs;

    pthread_t id;

    if (num > IXC_WORKER_NUM_MAX)
    {
        STDOUT("WARNING:the number of system worker max is %d\r\n", num);
        num = IXC_WORKER_NUM_MAX;
    }
    if (num < 1)
    {
        STDOUT("WARNING:wrong worker value %d\r\n", num);
        num = 1;
    }

    for (int n = 0; n < num; n++)
    {
        context = malloc(sizeof(struct ixc_worker_context));
        if (NULL == context)
        {
            STDERR("cannot malloc struct ixc_worker_context\r\n");
            return -1;
        }
        bzero(context, sizeof(struct ixc_worker_context));
        workers[n] = context;
    }

    for (int n = 0; n < num; n++)
    {
        context = workers[n];
        context->idx = n;
        rs = pthread_create(&id, NULL, &ixc_anylize_worker_start, context);
        if (rs != 0)
        {
            STDERR("create thread error\r\n");
            return -1;
        }
    }

    return 0;
}

void ixc_anylize_worker_uninit(void)
{
    struct ixc_worker_context *context;
    for (int n = 0; n < IXC_WORKER_NUM_MAX; n++)
    {
        context = workers[n];
        if (NULL == context)
            break;
        pthread_cancel(context->id);
        free(context);
    }
}

struct ixc_worker_context *ixc_anylize_worker_get(int seq)
{
    if (seq < 0 || seq > IXC_WORKER_NUM_MAX)
        return NULL;

    return workers[seq];
}