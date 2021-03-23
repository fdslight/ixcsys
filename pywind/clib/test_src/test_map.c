

#include<stdio.h>
#include "map.h"


int main(int argc,char *argv[])
{
    struct map *m;
    int rs=map_new(&m,4);
    int x=1000,*z;
    char is_found;

    rs=map_pre_alloc(m,256);
    rs=map_add(m,"hell",&x);
    //rs=map_add(m,"h",&x);
    
    z=map_find(m,"hell",&is_found);
    
    map_del(m,"hell",NULL);
    
    printf("%d %d %d\r\n",rs,is_found,*z);

    return 0;
}