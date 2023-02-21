#ifndef IXC_ROUTER_H
#define IXC_ROUTER_H

// 系统阻塞IO等待时间,请不要修改这个值,否则可能造成内存错误
#define IXC_IO_WAIT_TIMEOUT 10

/// 表示一个ARP数据包
#define IXC_FLAG_ARP 0
/// 表示是一个DHCP CLIENT数据包
#define IXC_FLAG_DHCP_CLIENT 1
/// 表示是一个DHCP SERVER数据包
#define IXC_FLAG_DHCP_SERVER 2
/// 表示一个Source filter数据包
#define IXC_FLAG_SRC_FILTER 3
/// 表示是一个带链路层头部的路由转发包
#define IXC_FLAG_ROUTE_FWD 4
/// 表示是一个vswitch数据包
#define IXC_FLAG_VSWITCH 5
/// IPv6隧道
#define IXC_FLAG_IP6_TUNNEL 6
/// 流复制
#define IXC_FLAG_TRAFFIC_COPY_MIN 32
#define IXC_FLAG_TRAFFIC_COPY_MAX 127

/// 最大允许96个任务分担执行
#define IXC_TRAFFIC_COPY_TASK_MAX 96

#include<sys/types.h>

/// 流量拷贝数据包格式
struct ixc_traffic_cpy_pkt_header{
    // 版本号,当前固定值为1
    unsigned char version;
    // 流量方向
    // 输出流量
#define IXC_TRAFFIC_OUT 0
    // 接收流量
#define IXC_TRAFFIC_IN 1
    unsigned char traffic_dir;
    char pad[6];
    // 数据包的时间（秒）
    unsigned long long sec_time;
    // 数据包的时间（微秒）
    unsigned long long usec_time;
};

/// 发送PPPoE数据包到Python
int ixc_router_pppoe_session_send(unsigned short protocol,unsigned short length,void *data);
/// 通知函数
int ixc_router_tell(const char *content);

void ixc_router_exit(void);

void ixc_router_md5_calc(void *data,int size,unsigned char *res);
/// 是否开启流量拷贝
int ixc_router_traffic_copy_is_enabled(void);
/// 主机序转网络序
unsigned long long ixc_htonll(unsigned long long v);
/// 获取netpkt拷贝进程数目
int ixc_router_traffic_copy_worker_num_get(void);

#endif