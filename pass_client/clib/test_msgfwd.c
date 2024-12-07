#include<stdio.h>
#include<string.h>

#include  "msgfwd.h"

int main(int argc,char *argv[])
{
    struct ixc_msgfwd_session session;
    char key[33];
    bzero(key,33);
    memset(key,13,32);

    int is_err=ixc_msgfwd_init(&session,key,"192.168.2.2",0,"0.0.0.0",8964,0);

    return 0;
}