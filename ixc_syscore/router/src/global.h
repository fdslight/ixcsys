/*** 全局共享变量  ***/
#ifndef IXC_GLOBAL_H
#define IXC_GLOBAL_H


int ixc_g_init(void);
void ixc_g_uninit(void);

/// 获取管理IP地址
void *ixc_g_manage_addr_get(int is_ipv6);

/// 设置管理地址
int ixc_g_manage_addr_set(unsigned char *addr,int is_ipv6);

/// 打开或者关闭网络
int ixc_g_network_enable(int enable);
int ixc_g_network_is_enabled(void);
/// 设置IPv6直通路由器地址
int ixc_g_ip6_pass_router_hwaddr_set(unsigned char *hwaddr);
/// 获取直通路由器地址
unsigned char *ixc_g_ip6_pass_router_hwaddr_get(void);


#endif