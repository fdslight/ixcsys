#include<arpa/inet.h>
#include<unistd.h>
#include<string.h>
#include<errno.h>
#include<sys/un.h>

#include "session.h"
#include "tcp_listener.h"

#include "../../../pywind/clib/debug.h"

static int tcp_listenfd=-1;
static int tcp_is_ipv6=0;

int ixc_tcp_listener_init(const unsigned char *byte_addr,int is_ipv6)
{
    int listenfd,rs;
    struct sockaddr_in in_addr;
    struct sockaddr_in6 in6_addr;

    if(is_ipv6) listenfd=socket(AF_INET6,SOCK_STREAM,0);
    else listenfd=socket(AF_INET,SOCK_STREAM,0);

    if(listenfd<0){
        STDERR("cannot create socket fileno\r\n");
        return -1;
    }

    memset(&in_addr,'0',sizeof(struct sockaddr_in));
    memset(&in6_addr,'0',sizeof(struct sockaddr_in6));

    
    if(is_ipv6){
        in6_addr.sin6_family=AF_INET6;
        memcpy(&(in6_addr.sin6_addr),byte_addr,16);
        in6_addr.sin6_port=htons(3260);
    }else{
        in_addr.sin_family=AF_INET;
        memcpy(&(in_addr.sin_addr.s_addr),byte_addr,4);
        in_addr.sin_port=htons(3260);
    }

    if(is_ipv6) rs=bind(listenfd,(struct sockaddr *)&in6_addr,sizeof(struct sockaddr_in6));
    else rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr));

    if(rs<0){
        STDERR("cannot bind npfwd\r\n");
        close(listenfd);

        return -1;
    }

    rs=listen(listenfd,10);

	if(rs<0){
		close(listenfd);
		STDERR("cannot listen socket\r\n");
		return -1;
	}

    tcp_listenfd=listenfd;
    tcp_is_ipv6=is_ipv6;

    return 0;
}


void ixc_tcp_listener_uninit(void)
{
    if(tcp_listenfd < 0) return;
    close(tcp_listenfd);
    tcp_listenfd=-1;
}

void ixc_tcp_listen(void)
{
    int rs,is_child=0;
    unsigned char buf[256];
    socklen_t addrlen;
    pid_t pid;

    while(1){
        rs=accept(tcp_listenfd,(struct sockaddr *)buf,&addrlen);
        if(rs<0) break;

        pid=fork();
        if(pid!=0) continue;

        is_child=1;
        break;
    }

    if(is_child) {
        ixc_tcp_listener_uninit();
        ixc_iscsi_session_create(rs,buf,addrlen,tcp_is_ipv6);
    }
}