#ifndef IXC_DHCP_SERVER_H
#define IXC_DHCP_SERVER_H

int ixc_dhcp_server_init(void);
void ixc_dhcp_server_uninit(void);
int ixc_dhcp_server_enable(int enable);
int ixc_dhcp_server_is_enabled(void);

#endif