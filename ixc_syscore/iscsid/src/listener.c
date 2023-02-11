#include<arpa/inet.h>
#include<unistd.h>
#include<string.h>
#include<errno.h>
#include<sys/un.h>

#include "listener.h"
#include "net_worker.h"

#include "../../../pywind/clib/debug.h"

static int iscsi_listener_socket_fd=-1;
static int iscsi_listener_socket_fd6=-1;
static int iscsi_listener_is_ipv6=0;

static int ixc_listener_socket_start(const char *bind_addr,int is_ipv6)
{
    int listenfd,rs;
    struct sockaddr_in in_addr;
    char buf[256];

    iscsi_listener_socket_fd=-1;
    iscsi_listener_socket_fd6=-1;
    iscsi_listener_is_ipv6=is_ipv6;

    listenfd=socket(AF_INET,SOCK_STREAM,0);

    if(listenfd<0){
        STDERR("cannot create socket fileno\r\n");
        return -1;
    }

    memset(&in_addr,'0',sizeof(struct sockaddr_in));

    in_addr.sin_family=AF_INET;
    inet_pton(AF_INET,bind_addr,buf);

    memcpy(&(in_addr.sin_addr.s_addr),buf,4);
	in_addr.sin_port=htons(3260);

    rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr));

    if(rs<0){
        STDERR("cannot bind socket\r\n");
        close(listenfd);

        return -1;
    }

    if (setsockopt(listenfd, SOL_SOCKET, SO_REUSEADDR, &(int){1}, sizeof(int)) < 0){
        STDERR("setsockopt(SO_REUSEADDR) failed\r\n");
        close(listenfd);
        return -1;
    }

    if(is_ipv6) iscsi_listener_socket_fd6=listenfd;
    else iscsi_listener_socket_fd=listenfd;

    rs=listen(listenfd,10);

    if(rs<0){
        STDERR("cannot listen socket\r\n");
        close(listenfd);
        return -1;
    }

    return 0;
}


int ixc_listener_init(void)
{
    int rs=ixc_listener_socket_start("127.0.0.1",0);

    return rs;
}

void ixc_listener_uninit(void)
{
  
}

void ixc_listener_loop(void)
{
    int sockfd=iscsi_listener_is_ipv6?iscsi_listener_socket_fd6:iscsi_listener_socket_fd;
    int rs,is_child_process=0;
    struct sockaddr client_addr;
    pid_t pid;

    socklen_t client_addrlen;

    while(1){
        rs=accept(sockfd,&client_addr,&client_addrlen);
        if(rs<0) continue;
        
        pid=fork();
        if(pid==0){
            is_child_process=1;
            break;
        }
    }

    if(is_child_process){
        // 子进程关闭父进程描述符
        close(sockfd);
        rs=ixc_net_worker_start(rs,&client_addr,client_addrlen,iscsi_listener_is_ipv6);
        if(rs<0) exit(EXIT_SUCCESS);
        ixc_net_worker_evloop();
    }

}