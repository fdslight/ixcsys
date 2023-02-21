/*负责系统的日志以及配置通信*/
#ifndef IXC_SYS_MSG_H
#define IXC_SYS_MSG_H

#include<sys/types.h>
#include<arpa/inet.h>
#include "../../../pywind/clib/ev/ev.h"

struct ixc_sys_msg{
    // 版本,固定值为1
    unsigned char version;
    // 消息类型
    // 规则告警
#define IXC_SYS_MSG_RULE_ALERT 0
    unsigned char type;
    // 消息长度
    unsigned char pad[6];
};

int ixc_sys_msg_send(unsigned char type, void *data, unsigned short size);

#endif