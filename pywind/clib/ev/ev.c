#include<string.h>
#include<time.h>

#include "ev.h"
#include "ev_select.h"
#include "ev_ext.h"

#include "../map.h"
#include "../debug.h"

static void ev_del_cb(void *data)
{
	struct ev *ev=data;
	ev->del_fn(ev);
}

static void ev_timeout_cb(void *data)
{
	struct ev *ev=data;

	if(NULL==ev->timeout_fn){
		STDERR("not set timeout_fn for fileno %d\r\n",ev->fileno);
	}else{
		ev->timeout_fn(ev);
	}
}

int ev_set_init(struct ev_set *ev_set,int force_select)
{
	struct map *m;
	struct time_wheel *time_wheel;
	int rs;
	
	bzero(ev_set,sizeof(struct ev_set));
	
	rs=map_new(&m,sizeof(int));
	
	if(rs<0){
		STDERR("cannot create map for ev_set\r\n");
		return -1;
	}
	
	// 此处创建定时器
	time_wheel=malloc(sizeof(struct time_wheel));
	if(NULL==time_wheel){
		map_release(m,NULL);
		STDERR("cannot malloc struct time_wheel\r\n");
		return -1;
	}
	rs=time_wheel_new(time_wheel,(EV_TIMEOUT_MAX*2)/10,10,ev_timeout_cb,16);
	if(rs<0){
		free(time_wheel);
		map_release(m,NULL);
		STDERR("cannot create time wheel\r\n");
		return -1;
	}
	
	if(force_select) rs=ev_select_init(ev_set);
	else rs=ev_ext_init(ev_set);
	
	if(rs<0){
		time_wheel_release(time_wheel);
		map_release(m,NULL);
		free(time_wheel);
		STDERR("cannot initialize ev_set\r\n");
	}

	ev_set->time_wheel=time_wheel;
	ev_set->m=m;
	ev_set->wait_timeout=10;
	ev_set->is_select=force_select;

	return rs;
}

void ev_set_uninit(struct ev_set *ev_set)
{
	// 释放所有文件描述符
	map_release(ev_set->m,ev_del_cb);
	
	// 释放扩展事件模型资源
	if(ev_set->is_select) ev_select_uninit(ev_set);
	else ev_ext_uninit(ev_set);

	time_wheel_release(ev_set->time_wheel);
}

struct ev *ev_create(struct ev_set *ev_set,int fileno)
{
	struct ev *ev=malloc(sizeof(struct ev));
	int rs;

	if(NULL==ev){
		STDERR("cannot malloc struct ev for fileno %d\r\n",fileno);
		return NULL;
	}
	bzero(ev,sizeof(struct ev));

	ev->fileno=fileno;

	rs=map_add(ev_set->m,(char *)(&fileno),ev);
	if(rs<0){
		free(ev);
		STDERR("cannot add to map for fileno %d\r\n",fileno);
		return NULL;
	}

	rs=ev_set->ev_create_fn(ev);
	if(rs<0){
		free(ev);
		map_del(ev_set->m,(char *)(&fileno),NULL);
		STDERR("cannot create event\r\n");
		return NULL;
	}

	return ev;
}

void ev_delete(struct ev_set *ev_set,struct ev *ev)
{
	ev_set->ev_delete_fn(ev);
	
	ev->next=NULL;
	ev->next=ev_set->del_head;
	ev_set->del_head=ev;
	ev->is_deleted=1;
}

int ev_modify(struct ev_set *ev_set,struct ev *ev,int ev_no)
{
	int is_readable=ev_no & EV_READABLE;
	int is_writable=ev_no & EV_WRITABLE;
	
	if(is_readable && !ev->is_added_read) {
		ev_set->add_read_ev_fn(ev);
		ev->is_added_read=1;
	}
	if(is_writable && !ev->is_added_write) {
		ev_set->add_write_ev_fn(ev);
		ev->is_added_write=1;
	}
	if(!is_readable && ev->is_added_read) {
		ev_set->del_read_ev_fn(ev);
		ev->is_added_read=0;
	}
	if(!is_writable && ev->is_added_write) {
		ev_set->del_write_ev_fn(ev);
		ev->is_added_write=0;
	}

	return 0;
}

int ev_loop(struct ev_set *ev_set)
{
	int rs=0;
	struct ev *ev,*t;

	while(1){
		rs=ev_set->ioloop_fn(ev_set);
		ev=ev_set->del_head;
		// 此处删除要删除的ev
		while(NULL!=ev){
			t=ev->next;
			free(ev);
			ev=t;
		}
		ev_set->del_head=NULL;
		if(rs<0) break;
	}

	return rs;
}

int ev_timeout_set(struct ev_set *ev_set,struct ev *ev,time_t timeout)
{
	struct time_data *tdata=time_wheel_add(ev_set->time_wheel,ev,timeout);

	if(NULL==tdata){
		STDERR("cannot add to timer for fileno %d\r\n",ev->fileno);
		return -1;
	}

	ev->tdata=tdata;
	ev->up_time=time(NULL);
	
	return 0;
}