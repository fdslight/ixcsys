#include<string.h>

#include "port_map.h"
#include "debug.h"

static struct ixc_port_map port_map;
static int port_map_is_initialized=0;

static void ixc_port_map_del_cb(void *data)
{
    free(data);
}

int ixc_port_map_init(void)
{
    struct map *m;
    int rs;

    bzero(&port_map,sizeof(struct ixc_port_map));

    rs=map_new(&m,3);
    if(0!=rs){
        STDERR("cannot create map for port_map\r\n");
        return -1;
    }

    port_map.m=m;
    port_map_is_initialized=1;

    return 0;
}

void ixc_port_map_uninit(void)
{
    map_release(port_map.m,ixc_port_map_del_cb);
    port_map_is_initialized=0;
}

int ixc_port_map_add(unsigned char *address,unsigned char protocol,unsigned short port)
{
    char key[3];
    int rs;
    struct ixc_port_map_record *r=NULL;
    
    port=htons(port);

    key[0]=protocol;
    memcpy(&key[1],&port,2);

    r=malloc(sizeof(struct ixc_port_map_record));
    if(NULL==r){
        STDERR("cannot malloc for struct ixc_port_map_record\r\n");
        return -1;
    }

    bzero(r,sizeof(struct ixc_port_map_record));

    rs=map_add(port_map.m,key,r);
    if(0!=rs){
        free(r);
        STDERR("cannot add to port_map\r\n");
        return -1;
    }

    r->protocol=protocol;
    r->port=port;
    memcpy(r->address,address,4);

    return 0;
}


void ixc_port_map_del(unsigned char protocol,unsigned short port)
{
    char key[3],is_found;
    struct ixc_port_map_record *r=NULL;
    
    port=htons(port);

    key[0]=protocol;
    memcpy(&key[1],&port,2);

    r=map_find(port_map.m,key,&is_found);
    if(NULL==r) return;

    map_del(port_map.m,key,ixc_port_map_del_cb);
}


struct ixc_port_map_record *ixc_port_map_find(unsigned char protocol,unsigned short port)
{
    char key[3],is_found;
    struct ixc_port_map_record *r=NULL;

    if(protocol!=6 && protocol!=17 && protocol!=136) return NULL;
    
    key[0]=protocol;
    memcpy(&key[1],&port,2);

    r=map_find(port_map.m,key,&is_found);

    return r;
}