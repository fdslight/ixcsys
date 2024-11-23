#include<stdio.h>
#include<string.h>

#include "router.h"
#include "syslog.h"
#include "npfwd.h"

void ixc_syslog_write(int level,const char *s)
{
    char buf[4096];
    unsigned int length=strlen(s);
    struct ixc_mbuf *m;

    if(length > IXC_SYSLOG_LENGTH_MAX){
        sprintf(buf,"syslog max length is %u,your syslog length is %u",IXC_SYSLOG_LENGTH_MAX,length);
        ixc_syslog_write(IXC_SYSLOG_LEVEL_WARN,buf);
        return;
    }

    switch(level){
        case IXC_SYSLOG_LEVEL_INFO:
            sprintf(buf,"INFO: ");
            break;
        case IXC_SYSLOG_LEVEL_WARN:
            sprintf(buf,"WARN: ");
            break;
        case IXC_SYSLOG_LEVEL_ERROR:
            sprintf(buf,"ERROR: ");
            break;
        default:
            sprintf(buf,"DEFAULT: ");
            break;
    }

    strcat(buf,s);
    m=ixc_mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        return;
    }

    m->begin=m->offset=IXC_MBUF_BEGIN;
    m->tail=m->end=m->begin+strlen(buf);

    memcpy(m->data+m->begin,buf,m->end-m->begin);
    
    ixc_npfwd_send_raw(m,0,IXC_FLAG_SYSLOG);
}