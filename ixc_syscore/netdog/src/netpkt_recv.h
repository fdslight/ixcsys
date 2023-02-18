/*网络包接收,接收路由器镜像过来的数据包*/
#ifndef IXC_NETPKT_RECV_H
#define IXC_NETPKT_RECV_H

#include "../../../pywind/clib/ev/ev.h"

int ixc_netpkt_recv_init(struct ev_set *ev_set);
void ixc_netpkt_recv_uninit(void);

// 获取通信端口
int ixc_netpkt_recv_port_get(unsigned short *port);


#endif