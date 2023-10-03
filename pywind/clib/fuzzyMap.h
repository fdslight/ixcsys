/* 
 *模糊映射算法,与map存在区别,如果存在相似的key,该库也会返回
 * 例如 key为 hell\0 ,那么查找hello也会返回,\0表示任意值的意思
 */
#ifndef __FUZZYMAP_H
#define __FUZZYMAP_H

typedef void (*fuzzyMap_del_func_t)(void *);
typedef void (*fuzzyMap_each_func_t)(void *);

struct fuzzyMap_node{
	// 临时用
	struct fuzzyMap_node *tmp;
	// 对应列表的上一个fuzzyMap_node
	struct fuzzyMap_node *list_prev;
	// 对应列表的下一个fuzzyMap_node
	struct fuzzyMap_node *list_next;
	// 节点树对应的前一个
	struct fuzzyMap_node *tree_prev;
	struct fuzzyMap_node *next_nodes[256];
	void *data;
	unsigned long long refcnt;
	unsigned char key_v;
	// 是否是数据节点
	char is_data_node;
};

struct fuzzyMap{
	struct fuzzyMap_node *tree_root;
	struct fuzzyMap_node *list_head;
	struct fuzzyMap_node *empty_head;
	unsigned int cur_alloc_num;
	unsigned int pre_alloc_num;
	unsigned char length;
};

int fuzzyMap_new(struct fuzzyMap **m,unsigned char length);
void fuzzyMap_release(struct fuzzyMap *m,fuzzyMap_del_func_t fn);

/// 预先分配资源
int fuzzyMap_pre_alloc(struct fuzzyMap *m,unsigned int size);

// 映射加入,如果key的字节值为0,表示允许任意值,这一点和map算法不同
int fuzzyMap_add(struct fuzzyMap *m,const char *key,void *data);
void fuzzyMap_del(struct fuzzyMap *m,const char *key,fuzzyMap_del_func_t fn);

/// @查找map结果
/// @param m 
/// @param key 
/// @param is_found 
/// @param match_count 匹配计数,表示有多少个值匹配
/// @return 
void *fuzzyMap_find(struct fuzzyMap *m,const char *key,char *is_found,unsigned int *match_count);
/// 数据遍历,注意遍历过程中不可删除数据
void fuzzyMap_each(struct fuzzyMap *m,fuzzyMap_each_func_t fn);

#endif


