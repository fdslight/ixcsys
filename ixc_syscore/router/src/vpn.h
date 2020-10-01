#ifndef IXC_VPN_H
#define IXC_VPN_H

int ixc_vpn_init(void);
void ixc_vpn_uninit(void);
int ixc_vpn_enable(int enable);

// VPN是否被打开
int ixc_vpn_is_opened(void);

#endif