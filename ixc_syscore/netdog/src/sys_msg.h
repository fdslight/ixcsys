/*负责系统的日志以及配置通信*/
#ifndef IXC_SYS_MSG_H
#define IXC_SYS_MSG_H

#include<sys/types.h>
#include "../../../pywind/clib/ev/ev.h"

struct ixc_sys_msg{
    // 版本,固定值为1
    unsigned char version;
    // 消息类型
    // 规则告警
#define IXC_SYS_MSG_RULE_ALERT 0
    // 获取网络包监听端口
#define IXC_SYS_MSG_RPC_REQ_PKT_MON_PORT 1
    // 返回网络数据包端口
#define IXC_SYS_MSG_RPC_RESP_PKT_MON_PORT 2
    // 加入规则
#define IXC_SYS_MSG_ADD_RULE 3
    // 删除规则
#define IXC_SYS_MSG_DEL_RULE 4
    unsigned char type;
    // 消息长度
    unsigned char pad[2];
};

int ixc_sys_msg_init(struct ev_set *ev_set);
void ixc_sys_msg_uninit(void);

int ixc_sys_msg_send(unsigned char type,void *data,size_t size);

#endif