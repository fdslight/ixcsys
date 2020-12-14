#include<arpa/inet.h>

#include "ip.h"
#include "ipv6.h"
#include "ipunfrag.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/netutils.h"

void ip_handle(struct mbuf *m)
{
    struct netutil_iphdr *header=(struct netutil_iphdr *)(m->data+m->offset);
    int version= (header->ver_and_ihl & 0xf0) >> 4;
    int is_supported=0;
    unsigned short frag_info,frag_off;
    int mf;
    
    // 检查是否是IPv6,如果是IPv6那么处理IPv6协议
    if(version==6){
        ipv6_handle(m);
        return;
    }

    switch(header->protocol){
        case 6:
        case 17:
        case 136:
            is_supported=1;
            break;
        default:
            break;
    }

    if(!is_supported){
        mbuf_put(m);
        return;
    }

    frag_info=ntohs(header->frag_info);
    frag_off=frag_info & 0x1fff;
    mf=frag_info & 0x2000;
    
    // 如果IP数据包有分包那么首先合并数据包
    if(mf!=0 || frag_off!=0) m=ipunfrag_add(m);
    if(NULL==m) return;

    

}