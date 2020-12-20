#include<string.h>

#include "tcp.h"
#include "debug.h"

static struct tcp_sessions tcp_sessions;

static void tcp_session_del_cb(void *data)
{

}

int tcp_init(void)
{
    struct map *m;
    int rs;

    bzero(&tcp_sessions,sizeof(struct tcp_sessions));

    rs=map_new(&m,36);
    if(0!=rs){
        STDERR("cannot create map for TCPv6\r\n");
        return -1;
    }
    tcp_sessions.sessions6=m;

    rs=map_new(&m,12);
    if(0!=rs){
        map_release(tcp_sessions.sessions6,NULL);
        STDERR("cannot create map for TCP\r\n");
        return -1;
    }
    tcp_sessions.sessions=m;

    return 0;
}

void tcp_uninit(void)
{
    map_release(tcp_sessions.sessions6,tcp_session_del_cb);
    map_release(tcp_sessions.sessions,tcp_session_del_cb);
}

int tcp_send(unsigned char *session_id,void *data,int length,int is_ipv6)
{
    return 0;
}

int tcp_close(unsigned char *session_id,int is_ipv6)
{
    return 0;
}

int tcp_window_set(unsigned char *session_id,int is_ipv6,unsigned short win_size)
{
    struct map *m=is_ipv6?tcp_sessions.sessions6:tcp_sessions.sessions;
    struct tcp_session *session;
    char is_found;

    session=map_find(m,(char *)session_id,&is_found);
    if(!is_found) return -1;
    session->my_window_size=win_size;

    return 0;
}

int tcp_send_reset(unsigned char *session_id,int is_ipv6)
{
    return 0;
}