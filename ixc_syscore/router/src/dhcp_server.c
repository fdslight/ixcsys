
#include "dhcp_server.h"

#include "../../../pywind/clib/debug.h"

static int dhcp_server_is_initialized=0;
static int dhcp_server_is_enabled=0;

int ixc_dhcp_server_init(void)
{

    dhcp_server_is_initialized=1;
    return 0;
}

void ixc_dhcp_server_uninit(void)
{
    dhcp_server_is_initialized=0;
}

int ixc_dhcp_server_enable(int enable)
{
    if(!dhcp_server_is_initialized){
        STDERR("dhcp server not initialized\r\n");
        return -1;
    }

    dhcp_server_is_enabled=enable;

    return 0;
}

inline
int ixc_dhcp_server_is_enabled(void)
{
    return dhcp_server_is_enabled;
}
