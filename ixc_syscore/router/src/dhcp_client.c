#include "dhcp_client.h"

#include "../../../pywind/clib/debug.h"

static int dhcp_client_is_initialized=0;
static int dhcp_client_is_enabled=0;

int ixc_dhcp_client_init(void)
{

    dhcp_client_is_initialized=1;
    return 0;
}

void ixc_dhcp_client_uninit(void)
{
    dhcp_client_is_initialized=0;
}

int ixc_dhcp_client_enable(int enable)
{
    if(!dhcp_client_is_initialized){
        STDERR("dhcp client not initialized\r\n");
        return -1;
    }

    dhcp_client_is_enabled=enable;

    return 0;
}

inline
int ixc_dhcp_client_is_enabled(void)
{
    return dhcp_client_is_enabled;
}
