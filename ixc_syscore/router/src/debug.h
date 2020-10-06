#ifndef IXC_DEBUG_H
#define IXC_DEBUG_H

#include "../../../pywind/clib/debug.h"

#ifdef DEBUG

#define IXC_PRINT_HWADDR(TEXT,X) DBG("%s %x:%x:%x:%x:%x:%x\r\n",X[0],X[1],X[2],X[3],X[4],X[5])
#define IXC_PRINT_IP(TEXT,X) DBG("%s %d.%d.%d.%d\r\n",TEXT,X[0],X[1],X[2],X[3])

#else

#define IXC_PRINT_HWADDR(TEXT,X)
#define IXC_PRINT_IP(TEXT,X)

#endif
#endif