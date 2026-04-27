

#include<stdio.h>

#include "../map.h"

void cb(void *x)
{
    printf("zzz\r\n");
}

int main(int argc,char *argv[])
{
    struct map *m;
    int rs=map_new(&m,4);
    int x=1000,*z;
    char is_found;
    int ka=1,kb=2;

    rs=map_pre_alloc(m,256);
    rs=map_add(m,(char *)(&ka),&x);
    rs=map_add(m,(char *)(&kb),&x);
    
    z=map_find(m,(char *)(&ka),&is_found);
    map_del(m,(char *)(&ka),NULL);
    map_each(m,cb);
    
    
    map_del(m,(char *)(&ka),NULL);
    map_del(m,(char *)(&ka),NULL);
    
    printf("%d %d %d\r\n",rs,is_found,*z);

    return 0;
}