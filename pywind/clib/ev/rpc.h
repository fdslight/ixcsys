/** 基于TCP套接字的RPC **/
#ifndef RPC_H
#define RPC_H

#include<sys/types.h>
#include<sys/socket.h>

#include "ev.h"

/// RPC最大数据大小,请不要修改这个值
#define RPC_DATA_MAX 0x10000
/// RPC请求数据结构体
struct rpc_req{
	// 总体数据长度,包括函数名和命名空间
	unsigned short tot_len;
	char pad[6];
	// 函数名
	char func_name[256];
	unsigned char arg_data[RPC_DATA_MAX];
};

/// RPC故障码定义
enum{
	RPC_ERR_NO=0,
	// 未找到函数名
	RPC_ERR_FN_NOT_FOUND,
	// 函数参数错误
	RPC_ERR_ARG,
	// 其他错误
	RPC_ERR_OTHER
};

/// RPC响应数据结构体,如果故障那么响应故障文本信息
struct rpc_resp{
	// 总体数据长度
	unsigned short tot_len;
	char pad[10];
	int is_error;
	unsigned char message[RPC_DATA_MAX];
};

/// RPC函数调用回调函数
typedef int (*rpc_fn_call_t)(void *,unsigned short,void *,unsigned short *);

struct rpc_session{
	/// 接收缓冲区
	unsigned char recv_buf[0x10000];
	unsigned char sent_buf[0x10000];
	char address[256];
	/// 是否处理完毕
	int handle_ok;
	/// 接收缓冲区结束位置
	int recv_buf_end;
	// 发送缓冲区开始位置
	int sent_buf_begin;
	int sent_buf_end;
	int fd;
	unsigned short port;
};

/// RPC函数信息
struct rpc_fn_info{
	struct rpc_fn_info *next;
	rpc_fn_call_t fn;
	char func_name[0xff];
};

struct rpc{
	struct rpc_fn_info *fn_head;
	struct ev *ev;
	struct ev_set *ev_set;
	int fileno;
	int is_ipv6;
};

/// 创建RPC对象
int rpc_create(struct ev_set *ev_set,const char *listen_addr,unsigned short port,int is_ipv6);
/// 注册函数
int rpc_fn_reg(const char *name,rpc_fn_call_t fn);
/// 取消函数注册
void rpc_fn_unreg(const char *name);
/// 调用函数
int rpc_fn_call(const char *name,void *arg,unsigned short arg_size,void *result,unsigned short *res_size);

/// 创建RPC会话
int rpc_session_create(int fd,struct sockaddr *sockaddr,socklen_t sock_len);
/// 发送数据到RPC缓冲区
int rpc_session_write_to_sent_buf(struct rpc_session *session,void *data,unsigned short size);
/// 检查是否发送完毕
int rpc_session_send_ok(struct rpc_session *session);
/// 删除RPC会话
void rpc_session_del(struct rpc_session *session);
/// 删除RPC对象
void rpc_delete(void);

#endif
