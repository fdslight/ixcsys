
#include<apra/inet.h>
#include<string.h>

#include "rpc.h"
#include "ev.h"
#include "../debug.h"

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

struct rpc *rpc_create(const char *listen_addr,unsigned short port,int is_ipv6,int is_nonblocking)
{
	return 0;
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
		STDERR("cannot reg rpc function %s,no memory for malloc struct rpc_fn_info\r\n");
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
	resp->is_error=info->fn(arg,arg_size,message,&msize);

}

struct rpc_session *rpc_session_create(struct rpc *rpc)
{
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
