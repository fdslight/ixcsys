
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

static int rpc_session_create(int fd,struct sockaddr *sockaddr,socklen_t sock_len);

static struct rpc_fn_info *rpc_fn_info_get(const char *name)
{
	struct rpc_fn_info *result=NULL,*t=rpc.fn_head;
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

static int rpc_fn_req(const char *name,void *arg,unsigned short arg_size,void *result,unsigned short *res_size)
{
	struct rpc_fn_info *info;
	char *s=result;

	*s='\0';

	info=rpc_fn_info_get(name);

	if(NULL==info){
		sprintf(s,"not found function %s",name);
		*res_size=strlen(s);
		
		return RPC_ERR_FN_NOT_FOUND;
	}

	return info->fn(arg,arg_size,result,res_size);
}

int rpc_create(struct ev_set *ev_set,const char *listen_addr,unsigned short port,int is_ipv6,rpc_fn_req_t fn_req)
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
	if(NULL!=fn_req) rpc.fn_req=fn_req;
	else rpc.fn_req=rpc_fn_req;

	rpc.ev=ev_create(ev_set,rpc.fileno);
	if(NULL==rpc.ev){
		STDERR("cannot create ev for RPC\r\n");
		close(listenfd);
		return -1;
	}

	EV_INIT_SET(rpc.ev,rpc_accept,NULL,NULL,NULL,NULL);
	
	rs=ev_modify(ev_set,rpc.ev,EV_READABLE,EV_CTL_ADD);

	return rs;
}

int rpc_fn_reg(const char *name,rpc_fn_call_t fn)
{
	struct rpc_fn_info *info=rpc_fn_info_get(name);
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
	info->next=rpc.fn_head;
	rpc.fn_head=info;
	
	return 0;
}

void rpc_fn_unreg(const char *name)
{
	struct rpc_fn_info *info=rpc_fn_info_get(name);
	struct rpc_fn_info *t=rpc.fn_head;
	if(NULL==info) return;
	if(rpc.fn_head==info){
		rpc.fn_head=info->next;
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


/// 解析RPC请求
static int rpc_session_parse_rpc_req(struct ev *ev,struct rpc_session *session)
{
	struct rpc_req *req=(struct rpc_req *)(session->recv_buf);
	unsigned short tot_len,res_size;
	char func_name[512];
	struct rpc_resp *resp=(struct rpc_resp *)(session->sent_buf);
	int err_code;

	// 缓冲区收到的数据必须等于大于2个字节
	if(session->recv_buf_end<2) return 0;

	tot_len=ntohs(req->tot_len);
	// 正常情况下tot len会比收到的数据大
	if(tot_len<session->recv_buf_end) return -1;
	// tot len的最小长度
	if(tot_len<264) return -1;
	if(tot_len>session->recv_buf_end) return 0;

	session->sent_buf_end=0;
	session->sent_buf_begin=0;

	bzero(func_name,512);
	memcpy(func_name,req->func_name,256);

	// 调用函数执行并返回结果
	err_code=rpc.fn_req(func_name,req->arg_data,tot_len-264,&(resp->message),&res_size);
	// 此处发送响应
	resp->is_error=htonl(err_code);
	resp->tot_len=htons(res_size+16);

	session->sent_buf_end=res_size+16;
	ev_modify(rpc.ev_set,ev,EV_WRITABLE,EV_CTL_ADD);
	ev->up_time=time(NULL);

	return 0;
}

static int rpc_session_readable_fn(struct ev *ev)
{
	ssize_t recv_size;
	int rs;
	struct rpc_session *session=ev->data;

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
				DBG("wrong RPC request\r\n");
				ev_delete(rpc.ev_set,ev);
				break;
			}
			break;
		}
		if(EAGAIN==errno) break;

		DBG("recv rpc data wrong from fd %d errno %d\r\n",ev->fileno,errno);
		ev_delete(rpc.ev_set,ev);
		break;
		
	}

	return 0;
}

static int rpc_session_writable_fn(struct ev *ev)
{
	ssize_t sent_size;
	struct rpc_session *session=ev->data;

	while(1){
		sent_size=send(ev->fileno,session->sent_buf+session->sent_buf_begin,session->sent_buf_end-session->sent_buf_begin,0);
		if(sent_size>=0){
			session->sent_buf_begin+=sent_size;
			// 数据已经被发送完毕那么重置
			if(session->sent_buf_begin==session->sent_buf_end){
				session->sent_buf_begin=0;
				session->sent_buf_end=0;
				ev_modify(rpc.ev_set,ev,EV_WRITABLE,EV_CTL_DEL);
				break;
			}
			continue;
		}

		if(EAGAIN==errno) break;
		ev_delete(rpc.ev_set,ev);
	}

	return 0;
}

static int rpc_session_timeout_fn(struct ev *ev)
{
	time_t now=time(NULL);
	
	if(now-ev->up_time<10){
		ev_timeout_set(rpc.ev_set,ev,10);
		return 0;
	}

	ev_delete(rpc.ev_set,ev);

	return 0;
}

static int rpc_session_del_fn(struct ev *ev)
{
	struct rpc_session *session=ev->data;

	DBG_FLAGS;

	close(session->fd);
	free(session);

	return 0;
}

static int rpc_session_create(int fd,struct sockaddr *sockaddr,socklen_t sock_len)
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

	if(ev_timeout_set(rpc.ev_set,ev,10)<0){
		STDERR("cannot set timeout for fd %d\r\n",fd);
	}

	EV_INIT_SET(ev,rpc_session_readable_fn,rpc_session_writable_fn,rpc_session_timeout_fn,rpc_session_del_fn,session);
	rs=ev_modify(rpc.ev_set,ev,EV_READABLE,EV_CTL_ADD);

	if(rs<0){
		ev_delete(rpc.ev_set,ev);
		STDERR("cannot add to readablefor fd %d\r\n",fd);
		return -1;
	}

	return 0;
}

void rpc_delete(void)
{
	struct rpc_fn_info *info=rpc.fn_head,*t;

	while(NULL!=info){
		t=info->next;
		free(info);
		info=t;
	}
}
