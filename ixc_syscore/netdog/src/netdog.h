#ifndef IXC_NETDOG_H
#define IXC_NETDOG_H

/// 获取工作线程数量
int ixc_netdog_worker_num_get(void);

unsigned long long ixc_ntohll(unsigned long long v);

void ixc_netdog_python_loop(void);

#endif