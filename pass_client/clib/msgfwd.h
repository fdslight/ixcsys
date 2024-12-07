/// 消息重定向客户端

#ifndef IXC_MSGFWD_H
#define IXC_MSGFWD_H

#include<sys/types.h>

#pragma pack(push)
#pragma pack(4)
struct ixc_msg_header{
    // key
    unsigned char key[16];
    // 要发送的网卡接口类型
    unsigned char if_type;
    // 填充字段
    unsigned char pad;
    // IP协议
    unsigned char ipproto;
    // 标志
    unsigned char flags;
};
#pragma pack(pop)

/// 包信息
struct ixc_msgfwd_pinfo{
    unsigned char if_type;
    unsigned char ipproto;
    unsigned char flags;
};

struct ixc_msgfwd_session{
    unsigned char key[16];
    unsigned char remote_host[16];
    unsigned short remote_port;
    unsigned char pad[2];
    int fd;
    int is_ipv6;
};

int ixc_msgfwd_init(struct ixc_msgfwd_session *session,\
const char *s_key,\
const char *remote_addr,unsigned short remote_port,\
const char *local_addr,unsigned short local_port,\
int is_ipv6);

void ixc_msgfwd_uninit(struct ixc_msgfwd_session *session);

int ixc_msgfwd_read(struct ixc_msgfwd_session *session,void *buf,unsigned int buf_size,struct ixc_msgfwd_pinfo *pinfo);
ssize_t ixc_msgfwd_write(struct ixc_msgfwd_session *session,void *buf,unsigned int buf_size,int fill_offset);

#endif