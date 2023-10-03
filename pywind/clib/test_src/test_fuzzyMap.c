

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
    int x=1000,y=2000,*z;
    unsigned int match_cnt;
    char is_found;

    rs=fuzzyMap_pre_alloc(m,256);
    rs=fuzzyMap_add(m,"hel\0",&x);
    rs=fuzzyMap_add(m,"her\0",&y);
    
    z=fuzzyMap_find(m,"herz",&is_found,&match_cnt);

    fuzzyMap_del(m,"hell",NULL);
    fuzzyMap_each(m,cb);
    fuzzyMap_del(m,"herd",NULL);
    
    if(is_found){
        printf("%d %d %d %d\r\n",rs,is_found,match_cnt,*z);
    }else{
        printf("not found key\r\n");
    }
    

    return 0;
}