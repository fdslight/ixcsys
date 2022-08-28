/** 多进程内存分配器,适合多进程共享内存 **/

#ifndef MP_MEMORY_H
#define MP_MEMORY_H

#include<sys/types.h>

/// 每个进程拥有的mp_memory结构
struct mp_memory{
	// 映射到本地进程的地址
	void *map_addr;
	// 自身内存的ID号
	unsigned int my_id;
};

/// 分配到的内存信息
struct mp_memory_blk {
	// 块开始位置
	unsigned int blk_start;
	// 占用的内存块数目
	unsigned int blk_num;
	// 实际大小,分配是以4KB为单位,但实际需要的内存不一定是4KB的倍数
	unsigned long long real_size;
};

#ifndef MP_MEMORY_QUEUE_SIZE 
#define MP_MEMORY_QUEUE_SIZE 256
#endif

/// 队列
struct mp_memory_queue{
	/// 下一个队列内存位置
	unsigned long long next;
	// 队列是否有效
	int is_valid;
	char pad[4];
};

/// 最大的PID数目,即最大允许多少个进程有独立内存块
#define MP_MEMORY_PID_NUM_MAX 1024

/// 共享内存的元信息
struct mp_memory_shm_meta{
	// 每个PID的内存块大小,单位为4KB
	unsigned long long every_pid_mem_blk_num[MP_MEMORY_PID_NUM_MAX];
	// 保存队列ring信息
	unsigned long long queue_ring[MP_MEMORY_QUEUE_SIZE][2];
	// 进程映射名字
	char process_alias_name[MP_MEMORY_PID_NUM_MAX][256];
	// 描述哪些PID拥有属于自己的内存块
	pid_t owner_pid[MP_MEMORY_PID_NUM_MAX];
	// 元数据大小
	unsigned int meta_size;
/// 每个内存块的信息
/// 读取锁
#define MP_MEMORY_BLK_INFO_LOCK_R 0x04
/// 写锁
#define MP_MEMORY_BLK_INFO_LOCK_W 0x02
/// 内存有效
#define MP_MEMORY_BLK_INFO_MEM_VALID 0x01
	// 描述内存块信息 unsigned char blk_info[],每个字节结构如下
	// bit0,bit1,bit2,bit3,bit4,bit_r_lock,bit_w_lock,is_valid
};


void *mp_memory_alloc(size_t size);
void mp_memory_free(void *ptr);

/// 主进程内存初始化
// param shm_fpath,共享内存路径
// 
int mp_memory_init_for_main_process(const char *shm_fpath);

/// 子进程内存初始化
int mp_memory_init_for_chld_process(void);
/// 子进程内存实例释放
void mp_memory_uninit_for_chld_process(void);

/// 获取新的内存块
struct mp_memory_blk *mp_memory_new(size_t size);
/// 删除内存块
void mp_memory_del(struct mp_memory_blk *memory);


#endif