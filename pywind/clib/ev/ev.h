#ifndef EV_H
#define EV_H

#include "../map.h"
#include "../timer.h"

#define EV_NO 0
#define EV_READABLE 1
#define EV_WRITABLE 2

/// 事件函数回调
// 返回0表示继续执行,非0表示发生错误
typedef int (*ev_fn_cb_t)(struct ev *);

/// 处理事件函数
typedef int (*ev_ioloop_fn_cb_t)(struct ev_set *);
/// 修改事件处理函数
typedef int (*ev_modify_fn_t)(struct ev *);

struct ev{
	struct ev *next;
	struct time_data *tdata;
	void *data;

	ev_fn_cb_t readable_fn;
	ev_fn_cb_t writable_fn;
	ev_fn_cb_t timeout_fn;
	
	// 加入事件回调
	ev_modify_fn_t add_read_ev_fn;
	ev_modify_fn_t add_write_ev_fn;
	// 删除事件回调
	ev_modify_fn_t del_read_ev_fn;
	ev_modify_fn_t del_write_ev_fn;
	
	time_t up_time;
	
	/// 是否已经加入读或者写事件
	int is_added_read;
	int is_added_write;
	
	int fileno;
	// 是否已经删除资源
	int is_deleted;
};

/// 事件集合
struct ev_set{
	struct ev *ev_head;
	struct map *m;
	
	ev_ioloop_fn_cb_t ioloop_fn;
	void *data;

	time_t wait_timeout;
	int is_select;
};

/// IO超时等待时间
#define EV_SET_TIMEOUT_WAIT(_ev_set) (_ev_set)->wait_timeout
/// 私有数据
#define EV_SET_PRIV_DATA (_ev_set) (_ev_set)->data

/// 事件集合初始化
// force_select 如果非0表示强制使用select事件模型,否则根据操作系统选择
int ev_set_init(struct ev_set *ev_set,int force_select,ev_ioloop_fn_cb_t ioloop_fn);
void ev_set_uninit(struct ev_set *ev_set);

/// 创建EV
int ev_create(struct ev_set *ev_set,struct ev **ev);
/// 删除事件
void ev_delete(struct ev_set *ev_set,int fileno);
/// 修改事件
int ev_modify(struct ev *ev,int fileno,int ev_no);
/// 事件循环
int ev_loop(struct ev_set *ev_set);
/// 设置超时事件超时时间
int ev_timeout_set(struct ev_set *ev_set,struct ev *ev,time_t timeout);


#endif
