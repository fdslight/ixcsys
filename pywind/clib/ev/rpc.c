
#include<arpa/inet.h>
#include<string.h>
#include<sys/types.h>
#include<sys/socket.h>
#include<unistd.h>

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
	return 0;
}

int rpc_create(struct ev_set *ev_set,const char *listen_addr,unsigned short port,int is_ipv6)
{
	int listenfd=-1;
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
		bind(listenfd,(struct sockaddr *)&in_addr,sizeof(struct in_addr));
	}
	listen(listenfd,10);
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
	char func_name[512];
	char message[RPC_DATA_MAX];
	unsigned short msize;
	struct rpc_fn_info *info;
	struct rpc_resp resp;

	bzero(func_name,512);
	strcpy(func_name,name);

	info=rpc_fn_info_get(rpc,func_name);
	// 未找到函数的处理方式
	if(NULL==info){
		sprintf(message,"cannot found function %s",func_name);
		return;
	}
	resp.is_error=info->fn(arg,arg_size,message,&msize);

}

struct rpc_session *rpc_session_create(struct rpc *rpc)
{
	return NULL;
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
