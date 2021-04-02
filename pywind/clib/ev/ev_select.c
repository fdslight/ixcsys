#include<sys/select.h>

#include "ev.h"
#include "ev_select.h"

/// 读集合
static fd_set ev_select_rset;
/// 写集合
static fd_set ev_select_wset;
static struct ev_select ev_select;

static int ev_select_add_read(struct ev *ev)
{	
	return 0;
}

static int ev_select_add_write(struct ev *ev)
{
	return 0;
}

static int ev_select_del_read(struct ev *ev)
{
	return 0;
}

static int ev_select_del_write(struct ev *ev)
{
	return 0;
}

static void ev_select_init_events(void *data)
{
	struct ev *ev=data;
	int fd_max;
	
	if(ev->is_added_read && !FD_ISSET(ev->fileno,&ev_select_rset)){
		FD_SET(ev->fileno,&ev_select_rset);
	}
	
	if(!ev->is_added_read && FD_ISSET(ev->fileno,&ev_select_rset)){
		FD_CLR(ev->fileno,&ev_select_rset);
	}
	
	if(ev->is_added_write && !FD_ISSET(ev->fileno,&ev_select_wset)){
		FD_SET(ev->fileno,&ev_select_wset);
	}
	
	if(!ev->is_added_write && FD_ISSET(ev->fileno,&ev_select_wset)){
		FD_CLR(ev->fileno,&ev_select_wset);
	}
}

static void ev_select_ev_handle(void *data)
{
	struct ev *ev=data;
	int is_readable=0,is_writable=0;
	
	if(FD_ISSET(ev->fileno,&ev_select_rset)) is_readable=1;
	if(FD_ISSET(ev->fileno,&ev_select_wset)) is_writable=1;
	
	if(is_readable && !ev->is_deleted){
	}
	
	if(is_writable && !ev->is_deleted){
	}
}

static int ev_select_ioloop(struct ev_set *ev_set)
{
	struct timeval timeval;
	int fd_max=0;
	int rs;
	
	while(1){
		// 遍历映射重新生成rset与wset
		map_each(ev_set->m,ev_select_init_events);
		
		rs=select(ev_select.fd_max+1,&ev_select_rset,&ev_select_wset,NULL,&timeval);
		
		if(rs<0){
			switch(errno){
				case EINVAL:
					break;
				default:
					break;
			}
			
			return -1;
		}
		
		
		map_each(ev_set->m,ev_select_ev_handle);
	}

	return 0;
}

int ev_select_init(struct ev_set *ev_set)
{
	bzero(&ev_select,sizeof(struct ev_select));
	
	FD_ZERO(&ev_select_rset);
	FD_ZERO(&ev_select_wset);
	
	return 0;
}

void ev_select_uninit(struct ev_set *ev_set)
{
	
}

