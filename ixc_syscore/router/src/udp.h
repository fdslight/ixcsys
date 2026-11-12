#ifndef IXC_UDP_H

#include "mbuf.h"

struct ixc_mbuf *ixc_udp_build_pkts(struct ixc_mbuf *mdata,int data_size,\
const unsigned char *dest_addr,const unsigned char *src_addr,int is_ipv6,\
unsigned short dest_port,unsigned short src_port,\
unsigned short mtu,int is_udplite,unsigned short udplite_csum_coverage);

#endif