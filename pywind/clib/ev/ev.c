
#include "ev.h"
#include "ev_select.h"
#include "ev_ext.h"

#include "../map.h"
#include "../debug.h"

static void ev_del_cb(void *data)
{
}

int ev_set_init(struct ev_set *ev_set,int force_select,ev_ioloop_fn_cb_t ioloop_fn)
{
	struct map *m;
	int rs;
	
	bzero(ev_set,sizeof(struct ev_set));
	
	ev_set->wait_timeout=10;
	ev_set->is_select=force_select;
	
	rs=map_new(&m,sizeof(int));
	
	if(rs<0){
		STDERR("cannot create map for ev_set\r\n");
		return -1;
	}
	
	ev_set->ioloop_fn=ioloop_fn;
	ev_set->m=m;
	
	// 此处创建定时器
	
	
	if(force_select) rs=ev_select_init(ev_set);
	else rs=ev_ext_init(ev_set);
	
	if(rs<0){
		map_relase(m,NULL);
		STDERR("cannot initialize ev_set\r\n");
	}

	return rs;
}

void ev_set_uninit(struct ev_set *ev_set)
{
	// 释放所有文件描述符
	map_release(ev_set->m,ev_del_cb);
	
	// 释放扩展事件模型资源
	if(ev_set->is_select) ev_select_uninit(ev_set);
	else ev_ext_uninit(ev_set);
	
}

int ev_create(struct ev_set *ev_set,struct ev **ev)
{
	return 0;
}

void ev_delete(struct ev_set *ev_set,int fileno)
{
	
}

int ev_modify(struct ev *ev,int fileno,int ev_no)
{
	int is_readable=ev_no & EV_READABLE;
	int is_writable=ev_no & EV_WRITABLE;
	
	if(is_readable && !ev->is_added_read) ev->add_read_ev_fn(ev);
	if(is_writable && !ev->is_added_write) ev->add_write_ev_fn(ev);
	
	if(!is_readable && ev->is_added_read) ev->del_read_ev_fn(ev);
	if(!is_writable && ev->is_added_write) ev->del_write_ev_fn(ev);
	
	return 0;
}

int ev_loop(struct ev_set *ev_set)
{
	int rs=ev_set->ioloop_fn(ev_set);
	
	return rs;
}

int ev_timeout_set(struct ev_set *ev_set,struct ev *ev,time_t timeout)
{
	return 0;
}