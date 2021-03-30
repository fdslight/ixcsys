#ifndef EV_H
#define EV_H

#include "../map.h"
#include "../timer.h"

#define EV_NO 0
#define EV_READABLE 1
#define EV_WRITABLE 2
#define EV_TIMEOUT 4

/// 事件函数回调
// 返回0表示继续执行,非0表示发生错误
typedef int (*ev_fn_cb_t)(struct ev *);

/// 处理事件函数
typedef int (*ev_ioloop_fn_cb_t)(void);

struct ev{
	struct ev *next;
	struct time_data *tdata;
	void *data;

	ev_fn_cb_t readable_cb;
	ev_fn_cb_t writable_cb;
	ev_fn_cb_t timeout_cb;
	
	int fileno;
};


/// 事件集合
struct ev_set{
	struct ev *ev_head;
	struct map *m;
	void *ev_model;

	time_t wait_timeout;
};

/// 事件集合初始化
// force_select 如果非0表示强制使用select事件模型,否则根据操作系统选择
int ev_set_init(struct ev_set *ev_set,int force_select);
void ev_set_uninit(struct ev_set *ev_set);

/// 创建EV
int ev_create(struct ev_set *ev_set,struct ev **ev);
/// 删除事件
void ev_delete(struct ev_set *ev_set,int fileno);
/// 修改事件
int ev_modify(struct ev_set *ev_set,int fileno,int ev_no);
/// 事件循环
int ev_loop(struct ev_set *ev_set);


#endif
