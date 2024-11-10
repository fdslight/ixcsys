#ifndef IXC_VDISK_H
#define IXC_VDISK_H

struct ixc_vdisk_header{
    char magic[16];
    int version;
    // 数据块类型
    int blk_type;
    // 是否需要包含备份,如果这个标志不为0,表示磁盘数据需要存储两份
    int need_backup;
    // 数据的开始位置
    int data_offset;
    // 磁盘大小
    unsigned long long disk_size;
    // 下一个数据块的位置
    unsigned char next_blk_path[1024];
    // 下一个备份数据块的位置
    unsigned char next_backup_blk_path[1024];
};


#endif