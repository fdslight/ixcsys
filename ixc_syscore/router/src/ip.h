#ifndef IXC_IP_H
#define IXC_IP_H

#include "mbuf.h"

#define IXC_IPADDR_UNSPEC {0x00,0x00,0x00,0x00}
#define IXC_IPADDR_BROADCAST {0xff,0xff,0xff,0xff}

int ixc_ip_init(void);

void ixc_ip_handle(struct ixc_mbuf *mbuf);
int ixc_ip_send(struct ixc_mbuf *m);
// 开启或者关闭非系统DNS
int ixc_ip_no_system_dns_drop_enable(int enable);

int ixc_ip_enable_4in6(int enable,const unsigned char *peer_ip6_addr);
int ixc_ip_4in6_is_enabled(void);

unsigned char *ixc_ip_4in6_peer_address_get(void);

// 提供直通访问,便于管理桥接后的光猫等设备
int ixc_ip_rewrite_for_pass_enable(int enable);
int ixc_ip_rewrite_for_pass_set(const unsigned char *dest_addr,const unsigned char *src_addr,const unsigned char *new_src_addr);
int ixc_ip_rewrite_for_pass_is_allowed(const unsigned char *dest_addr,const unsigned char *src_addr,int is_src);
int ixc_ip_rewrite_for_pass_do(struct ixc_mbuf *m,int is_src);

unsigned char *ixc_ip_rewrite_for_pass_new_src_addr_get(void);
unsigned char *ixc_ip_rewrite_for_pass_old_src_addr_get(void);

void ixc_ip_uninit(void);



#endif