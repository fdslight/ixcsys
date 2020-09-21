#ifndef IXC_DHCP_CLIENT_H
#define IXC_DHCP_CLIENT_H


int ixc_dhcp_client_init(void);
void ixc_dhcp_client_uninit(void);
int ixc_dhcp_client_enable(int enable);
int ixc_dhcp_client_is_enabled(void);

#endif