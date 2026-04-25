

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

    int k1=2000;
    int k2=3000;

    rs=map_pre_alloc(m,256);
    rs=map_add(m,(char *)&k1,&x);
    rs=map_add(m,(char *)&k2,&x);
    
    z=map_find(m,(char *)&k1,&is_found);
    map_del(m,(char *)&k1,NULL);
    map_each(m,cb);
    
    
    map_del(m,(char *)&k2,NULL);
    
    printf("%d %d %d\r\n",rs,is_found,*z);

    return 0;
}