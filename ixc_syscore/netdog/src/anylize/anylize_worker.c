#include<string.h>
#include "anylize_worker.h"

// sys_msg是否被锁住
static int anylize_worker_sys_msg_is_locked=0;
// 网络数据包是否被锁住
static int anylize_worker_netpkt_is_locked=0;

static struct ixc_worker_context *workers[IXC_WORKER_NUM_MAX];


static void *ixc_anylize_worker_start(void *thread_seq)
{
    STDOUT("pthread_id %ld\r\n",pthread_self());

    return NULL;
}

int ixc_anylize_worker_init(void)
{
    bzero(workers,sizeof(NULL)*IXC_WORKER_NUM_MAX);
    return 0;
}

int ixc_anylize_create_workers(int num)
{
    struct ixc_worker_context *context=NULL;
    int rs;

    pthread_t id;

    if(num>IXC_WORKER_NUM_MAX){
        STDOUT("WARNING:the number of system worker max is %d\r\n",num);
        num=IXC_WORKER_NUM_MAX;
    }
    if(num<1){
        STDOUT("WARNING:wrong worker value %d\r\n",num);
        num=1;
    }

    for(int n=0;n<num;n++){
        context=malloc(sizeof(struct ixc_worker_context));
        if(NULL==context){
            STDERR("cannot malloc struct ixc_worker_context\r\n");
            return -1;
        }
        bzero(context,sizeof(struct ixc_worker_context));
        workers[n]=context;
    }

    for(int n=0;n<num;n++){
        context=workers[n];
        rs=pthread_create(&id,NULL,&ixc_anylize_worker_start,&n);
        if(rs!=0){
            STDERR("create thread error\r\n");
            return -1;
        }
    }

    return 0;
}

void ixc_anylize_worker_uninit(void)
{

}

int ixc_anylize_worker_lock_get(int lock_flags)
{
    int *ptr;

    if(IXC_ANYLIZE_WORKER_LOCK_SYS_MSG==lock_flags){
        ptr=&anylize_worker_sys_msg_is_locked;
    }else{
        ptr=&anylize_worker_netpkt_is_locked;
    }

    while(1){
        if(*ptr==0){
            *ptr=1;
            break;
        }
    }

    return 0;
}

void ixc_anylize_worker_unlock(int lock_flags)
{
    
}