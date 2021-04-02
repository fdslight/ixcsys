
#include<arpa/inet.h>
#include<string.h>
#include<sys/types.h>
#include<sys/socket.h>
#include<unistd.h>
#include<errno.h>

#include "rpc.h"
#include "ev.h"
#include "../debug.h"

static struct rpc rpc;

static struct rpc_fn_info *rpc_fn_info_get(struct rpc *rpc,const char *name)
{
	struct rpc_fn_info *result=NULL,*t=rpc->fn_head;
	while(NULL!=t){
		if(strcmp(name,t->func_name)){
			t=t->next;
			continue;
		}
		result=t;
		break;
	}

	return result;
}

static int rpc_accept(struct ev *ev)
{
	int rs;
	struct sockaddr sockaddr;
	socklen_t addrlen;

	while(1){
		rs=accept(rpc.fileno,&sockaddr,&addrlen);
		if(rs<0) break;
		rpc_session_create(rs,&sockaddr,addrlen);
	}

	return 0;
}

int rpc_create(struct ev_set *ev_set,const char *listen_addr,unsigned short port,int is_ipv6)
{
	int listenfd=-1,rs=0;
	struct sockaddr_in in_addr;
	struct sockaddr_in6 in6_addr;
	char buf[256];
	
	if(is_ipv6) listenfd=socket(AF_INET6,SOCK_STREAM,0);
	else listenfd=socket(AF_INET,SOCK_STREAM,0);

	if(listenfd<0){
		STDERR("cannot create listen fileno\r\n");
		return -1;
	}

	memset(&in_addr,'0',sizeof(struct sockaddr_in));
	memset(&in6_addr,'0',sizeof(struct sockaddr_in6));

	in_addr.sin_family=AF_INET;
	
	if(is_ipv6) inet_pton(AF_INET6,listen_addr,buf);
	else inet_pton(AF_INET,listen_addr,buf);

	memcpy(&(in_addr.sin_addr.s_addr),buf,4);
	in_addr.sin_port=htons(port);

	if(is_ipv6){
	}else{
		rs=bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct sockaddr));
	}

	if(rs<0){
		STDERR("cannot bind address %s %d errno:%d\r\n",listen_addr,port,errno);
		close(listenfd);
		return -1;
	}
	
	rs=listen(listenfd,10);
	if(rs<0){
		STDERR("cannot listen address %s %d errno:%d\r\n",listen_addr,port,errno);
		close(listenfd);
		return -1;
	}

	rs=ev_setnonblocking(listenfd);
	if(rs<0){
		close(listenfd);
		STDERR("cannot set nonblocking\r\n");
		return -1;
	}

	bzero(&rpc,sizeof(struct rpc));

	rpc.is_ipv6=is_ipv6;
	rpc.fileno=listenfd;
	rpc.ev_set=ev_set;

	rpc.ev=ev_create(ev_set,rpc.fileno);
	if(NULL==rpc.ev){
		STDERR("cannot create ev for RPC\r\n");
		close(listenfd);
		return -1;
	}

	EV_INIT_SET(rpc.ev,rpc_accept,NULL,NULL,NULL,NULL);
	
	DBG("create rpc OK\r\n");

	return ev_modify(ev_set,rpc.ev,EV_READABLE);
}

int rpc_fn_reg(struct rpc *rpc,const char *name,rpc_fn_call_t fn)
{
	struct rpc_fn_info *info=rpc_fn_info_get(rpc,name);
	if(NULL==info){
		STDERR("cannot reg rpc function %s,it is exists\r\n",name);
		return -1;
	}
	if(strlen(name)>0xff){
		STDERR("cannot reg rpc function %s,the function name is too long\r\n",name);
		return -2;
	}

	info=malloc(sizeof(struct rpc_fn_info));
	if(NULL==info){
		STDERR("cannot reg rpc function %s,no memory for malloc struct rpc_fn_info\r\n",name);
		return -3;
	}
	bzero(info,sizeof(struct rpc_fn_info));
	strcpy(info->func_name,name);
	info->fn=fn;
	info->next=rpc->fn_head;
	rpc->fn_head=info;
	
	return 0;
}

void rpc_fn_unreg(struct rpc *rpc,const char *name)
{
	struct rpc_fn_info *info=rpc_fn_info_get(rpc,name);
	struct rpc_fn_info *t=rpc->fn_head;
	if(NULL==info) return;
	if(rpc->fn_head==info){
		rpc->fn_head=info->next;
		free(info);
		return;
	}

	while(NULL!=t){
		if(t->next==info){
			t->next=info->next;
			free(info);
			break;
		}
		t=t->next;
	}
}

void rpc_fn_call(struct rpc *rpc,const char *name,void *arg,unsigned short arg_size)
{
	char message[RPC_DATA_MAX];
	unsigned short msize;
	struct rpc_fn_info *info;
	struct rpc_resp resp;

	info=rpc_fn_info_get(rpc,name);
	// 未找到函数的处理方式
	if(NULL==info){
		sprintf(message,"cannot found function %s",name);
		return;
	}
	resp.is_error=info->fn(arg,arg_size,message,&msize);
}

/// 解析RPC请求
static int rpc_session_parse_rpc_req(struct ev *ev,struct rpc_session *session)
{
	struct rpc_req *req=(struct rpc_req *)(session->recv_buf);
	unsigned short tot_len;
	char func_name[512];

	// 缓冲区收到的数据必须等于大于2个字节
	if(session->recv_buf_end<2) return 0;

	tot_len=ntohs(req->tot_len);
	// 正常情况下tot len会比收到的数据大
	if(tot_len<session->recv_buf_end) return -1;

	bzero(func_name,512);
	memcpy(func_name,req->func_name,256);

	// 调用函数执行并返回结果
	rpc_fn_call(&rpc,func_name,req->arg_data,tot_len-264);


	return 0;
}

static int rpc_session_readable_fn(struct ev *ev)
{
	ssize_t recv_size;
	int rs;
	struct rpc_session *session=ev->data;

	DBG_FLAGS;

	for(int n=0;n<10;n++){
		recv_size=recv(ev->fileno,&session->recv_buf[session->recv_buf_end],0xffff-session->recv_buf_end,0);
		// 如果接收到数据为0说明对端已经关闭连接
		if(0==recv_size){
			ev_delete(rpc.ev_set,ev);
			break;
		}
		if(recv_size>0){
			session->recv_buf_end+=recv_size;
			rs=rpc_session_parse_rpc_req(ev,session);
			if(rs<0){
				ev_delete(rpc.ev_set,ev);
				break;
			}
		}
		if(EAGAIN!=errno){
			ev_delete(rpc.ev_set,ev);
			break;
		}else{
			break;
		}
	}

	return 0;
}

static int rpc_session_writable_fn(struct ev *ev)
{
	DBG_FLAGS;
	return 0;
}

static int rpc_session_timeout_fn(struct ev *ev)
{
	DBG_FLAGS;
	return 0;
}

static int rpc_session_del_fn(struct ev *ev)
{
	DBG_FLAGS;
	return 0;
}

int rpc_session_create(int fd,struct sockaddr *sockaddr,socklen_t sock_len)
{
	struct rpc_session *session=malloc(sizeof(struct rpc_session));
	int rs;
	struct ev *ev;

	if(NULL==session){
		close(fd);
		STDERR("cannot create session for fd %d\r\n",fd);
		return -1;
	}

	if(ev_setnonblocking(fd)<0){
		close(fd);
		STDERR("cannot set nonblocking\r\n");
		free(session);
		return -1;
	}

	bzero(session,sizeof(struct rpc_session));
	session->fd=fd;

	ev=ev_create(rpc.ev_set,fd);

	if(NULL==ev){
		free(session);
		close(fd);
		STDERR("cannot create event for fd %d\r\n",fd);
		return -1;
	}

	EV_INIT_SET(ev,rpc_session_readable_fn,rpc_session_writable_fn,rpc_session_timeout_fn,rpc_session_del_fn,session);
	rs=ev_modify(rpc.ev_set,ev,EV_READABLE);

	if(rs<0){
		ev_delete(rpc.ev_set,ev);
		free(session);
		close(fd);
		STDERR("cannot add to readablefor fd %d\r\n",fd);
		return -1;
	}

	return 0;
}

int rpc_session_write_to_sent_buf(struct rpc_session *session,void *data,unsigned short size)
{
	return 0;
}

int rpc_session_send_ok(struct rpc_session *session)
{
	if(session->sent_buf_begin==session->sent_buf_end) return 1;
	return 0;
}

void rpc_session_del(struct rpc *rpc,struct rpc_session *session)
{
}

void rpc_delete(struct rpc *rpc)
{
}
