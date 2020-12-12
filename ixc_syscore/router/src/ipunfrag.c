#include<string.h>

#include "ipunfrag.h"

#include "../../../pywind/clib/netutils.h"

static struct ixc_ipunfrag ipunfrag;
static int ipunfrag_is_initialized=0;

int ixc_ipunfrag_init(void)
{
    bzero(&ipunfrag,sizeof(struct ixc_ipunfrag));
    ipunfrag_is_initialized=1;
    return 0;
}

void ixc_ipunfrag_uninit(void)
{
    ipunfrag_is_initialized=0;
}

struct ixc_mbuf *ixc_ipungrag_get(void)
{
    return NULL;
}

int ixc_ipunfrag_add(struct ixc_mbuf *m)
{
    struct ixc_mbuf *new_mbuf;
    struct netutil_iphdr *header;
    int mf,rs,max_v,header_len;
    unsigned short frag_info,offset,tot_len;
    char key[10],is_found;

    if(!ipunfrag_is_initialized){
        ixc_mbuf_put(m);
        STDERR("please init ipunfrag\r\n");
        return -1;
    }

    header=(struct netutil_iphdr *)(m->data+m->offset);
    header_len=(header->ver_and_ihl & 0x0f) * 4; 

    frag_info=ntohs(header->frag_info);

    offset=frag_info & 0x1fff;
    mf=frag_info & 0x2000;
    
    memcpy(&key[0],header->src_addr,4);
    memcpy(&key[4],header->dst_addr,4);
    memcpy(&key[8],(char *)(&(header->id)),2);

    // 如果不是第一个分包检查key是否存在
    if(offset!=0){
        new_mbuf=map_find(ipunfrag.m,key,&is_found);
        // key不存在那么直接丢弃数据包
        if(NULL==new_mbuf){
            ixc_mbuf_put(m);
            return -1;
        }
    }else{
        // 检查是否发送了重复的数据包,如果是重复的数据包那么直接丢弃
        new_mbuf=map_find(ipunfrag.m,key,&is_found);
        if(NULL!=new_mbuf){
            ixc_mbuf_put(m);
            return -1;
        }
        new_mbuf=ixc_mbuf_get();
        if(NULL==new_mbuf){
            STDERR("cannot get mbuf for ip ipunfrag\r\n");
            ixc_mbuf_put(m);
            return -1;
        }
        rs=map_add(ipunfrag.m,key,new_mbuf);
        if(rs!=0){
            ixc_mbuf_put(new_mbuf);
            ixc_mbuf_put(m);
            STDERR("cannot to map\r\n");
            return -1;
        }
        new_mbuf->next=NULL;
        new_mbuf->netif=m->netif;
        new_mbuf->is_ipv6=0;
        new_mbuf->from=m->from;
        new_mbuf->begin=m->offset;
        new_mbuf->offset=m->offset;
        new_mbuf->tail=m->tail;
        new_mbuf->end=m->tail;
        new_mbuf->link_proto=m->link_proto;
    }

    tot_len=ntohs(header->tot_len);

    // 检查分包长度的合法性
    max_v=new_mbuf->offset+offset * 8 + tot_len;
    if(max_v>IXC_MBUF_DATA_MAX_SIZE){
        STDERR("security problem,invalid ip fragment length\r\n");
        ixc_mbuf_put(m);
        ixc_mbuf_put(new_mbuf);
        return -1;
    }

    memcpy(new_mbuf->data+new_mbuf->offset+offset * 8,m->data+m->offset+header_len,tot_len-header_len);

    // 如果是最后一个分片的处理方法
    if(mf==0){
        
    }

    return 0;
}