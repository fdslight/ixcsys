

#include<stdio.h>

#include "../fuzzyMap.h"

void cb(void *x)
{
    printf("zzz\r\n");
}

int main(int argc,char *argv[])
{
    struct fuzzyMap *m;
    int rs=fuzzyMap_new(&m,4);
    int x=1000,*z;
    unsigned int match_cnt;
    char is_found;

    rs=fuzzyMap_pre_alloc(m,256);
    rs=fuzzyMap_add(m,"hell",&x);
    rs=fuzzyMap_add(m,"herd",&x);
    
    z=fuzzyMap_find(m,"hell",&is_found,&match_cnt);
    fuzzyMap_del(m,"hell",NULL);
    fuzzyMap_each(m,cb);
    
    
    fuzzyMap_del(m,"herd",NULL);
    
    printf("%d %d %d match_count:%d\r\n",rs,is_found,match_cnt,*z);

    return 0;
}