#ifndef IXC_DHCP_CLIENT_H
#define IXC_DHCP_CLIENT_H

#include<time.h>

#include "mbuf.h"

struct ixc_dhcp_client{
    time_t up_time;
    // DHCP租用时间
    time_t dhcp_lease_time;
    unsigned int xid;
    int is_got_ip;
    int is_sent_renew;
    // 是否已经选择了DHCP服务器
    int is_selected;
    char hostname[256];
    char vendor[256];
    unsigned char nameserver1[4];
    unsigned char nameserver2[4];
    unsigned char gateway[4];
    // 选择的DHCP服务器硬件地址
    unsigned char selected_shwaddr[6];
    unsigned short dhcp_secs;
};

int ixc_dhcp_client_init(void);
void ixc_dhcp_client_uninit(void);
int ixc_dhcp_client_enable(int enable);
int ixc_dhcp_client_is_enabled(void);

void ixc_dhcp_client_handle(struct ixc_mbuf *m);

#endif