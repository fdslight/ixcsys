#include<string.h>
#include<sys/uio.h>
#include<stdio.h>

#include "../netif/tuntap.h"


int main(int argc,char *argv[])
{
    char ifname[256];
    char buffer1[4096];
    char buffer2[4096];
    struct iovec vec[2];
    const char *s;

    strcpy(ifname,"tap0");

    int fd=tundev_create(ifname);
    tundev_up(ifname);
    
    vec[0].iov_base=buffer1;
    vec[0].iov_len=4096;

    vec[1].iov_base=buffer2;
    vec[1].iov_len=4096;

    buffer1[0]=0xff;
    buffer2[0]=0xff;

    ssize_t x=readv(fd,vec,2);

    for(int n=0;n<2;n++){
        s=vec[n].iov_base;
        printf("%d %d %d--\r\n",s[0],vec[n].iov_len,x);
    }

    x=readv(fd,vec,2);

    for(int n=0;n<2;n++){
        s=vec[n].iov_base;
        printf("%d %d %d\r\n",s[0],vec[n].iov_len,x);
    }


    tundev_close(fd,ifname);

    return 0;
}