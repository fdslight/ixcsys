#include "vpn.h"

static int vpn_enable=0;
static int vpn_is_initialized=0;

int ixc_vpn_init(void)
{
    vpn_is_initialized=1;
    return 0;
}

void ixc_vpn_uninit(void)
{
    vpn_is_initialized=0;
    return;
}

int ixc_vpn_enable(int enable)
{
    vpn_enable=enable;
    return 0;
}

inline
int ixc_vpn_is_opened(void)
{
    return vpn_enable;
}