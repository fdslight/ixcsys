#ifndef IXC_SYSLOG_H
#define IXC_SYSLOG_H

/// 注意长度一定得小于mbuf缓冲区的值
#define IXC_SYSLOG_LENGTH_MAX 2048

// syslog等级
enum{
    IXC_SYSLOG_LEVEL_INFO=0,
    IXC_SYSLOG_LEVEL_WARN,
    IXC_SYSLOG_LEVEL_ERROR
};

void ixc_syslog_write(int level,const char *s);

#endif