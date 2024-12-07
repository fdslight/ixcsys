#include<string.h>
#include<stdio.h>
#include<unistd.h>
#include<sys/un.h>
#include<arpa/inet.h>
#include<sys/socket.h>

#include "msgfwd.h"
#include "../../pywind/clib/debug.h"

static int __ixc_msgfwd_hex2binkey(const char *hex_key,unsigned char *res,unsigned int res_length)
{
    int err=0,ascii_v,i=1,j=0;
    int tot_length=strlen(hex_key);
    unsigned char v=0,res_v=0;

    // 如果不是偶数,那么补齐最前面的一个数
    if(tot_length%2!=0){
        i++;
        tot_length+=1;
    }

    if(tot_length*2<res_length){
        err=1;
        return 1;
    }

    while(*hex_key!='\0'){
        err=1;
        ascii_v=*hex_key;
        if(ascii_v>=0x30 && ascii_v<=0x39){
            err=0;
            v=ascii_v-0x30;
        }

        if(ascii_v>=0x41 && ascii_v<=0x46){
            err=0;
            v=ascii_v-0x41+0x0a;
        }

        if(ascii_v>=0x61 && ascii_v<=0x66){
            err=0;
            v=ascii_v-0x61+0x0a;
        }

        if(err) break;

        if(i%2==0){
            res_v=res_v | v;
            res[j]=res_v;
            res_v=0;
            j++;
        }else{
            res_v=v << 4;
        }
        i++;
        hex_key++;
    }

    return err;
}

int ixc_msgfwd_init(struct ixc_msgfwd_session *session,\
const char *s_key,\
const char *remote_addr,unsigned short remote_port,\
const char *local_addr,unsigned short local_port,\
int is_ipv6)
{
    unsigned char bin_key[16];

    if(strlen(s_key)!=32){
        STDERR("wrong s_key length\r\n");
        return -1;
    }

    int listenfd,rs;
    struct sockaddr_in in_addr;
    struct sockaddr_in6 in6_addr;
    char buf[256];

    listenfd=socket(AF_INET,SOCK_DGRAM,0);

    if(listenfd<0){
        STDERR("cannot create socket fileno\r\n");
        return -1;
    }

    memset(&in_addr,'0',sizeof(struct sockaddr_in));
    memset(&in6_addr,'0',sizeof(struct sockaddr_in6));

    in_addr.sin_family=AF_INET;
    in6_addr.sin6_family=AF_INET;
    
    inet_pton(AF_INET,"0.0.0.0",buf);
    inet_pton(AF_INET6,"::",buf);

    memcpy(&(in_addr.sin_addr.s_addr),buf,4);
    memcpy(&(in6_addr).sin6_addr,buf,16);

	in_addr.sin_port=htons(local_port);
    in6_addr.sin6_port=htons(local_port);

    if(is_ipv6){
        rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr_in6));
    }else{
        rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr_in));
    }

    if(rs<0){
        STDERR("cannot bind msgfwd socket\r\n");
        close(listenfd);

        return -1;
    }

    bzero(session,sizeof(struct ixc_msgfwd_session));

    session->fd=rs;
    session->is_ipv6=is_ipv6;
    session->remote_port=htons(remote_port);

    if(is_ipv6){
        inet_pton(AF_INET6,remote_addr,session->remote_host);
    }else{
        inet_pton(AF_INET,remote_addr,session->remote_host);
    }
    
    return 0;
}

void ixc_msgfwd_uninit(struct ixc_msgfwd_session *session)
{
    close(session->fd);
}

int ixc_msgfwd_read(struct ixc_msgfwd_session *session,void *buf,unsigned int buf_size)
{
    return 0;
}

ssize_t ixc_msgfwd_write(struct ixc_msgfwd_session *session,void *buf,unsigned int buf_size,int fill_offset)
{
    return -1;
}
