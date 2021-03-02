#include<stdio.h>
#include<time.h>
#include<unistd.h>

#include "../src/tcp_buf.h"

int main(int argc,char *arv[])
{
    struct tcp_buf tcp_buf;
    char *s1="hello";
    char *s2="world";
    char s3[32];
    int sent_size;

    tcp_buf_init(&tcp_buf);

    tcp_buf.begin=0xfff4;
    tcp_buf.end=0xfff4;

    tcp_buf_copy_to_tcp_buf(&tcp_buf,s1,6);
    tcp_buf_copy_to_tcp_buf(&tcp_buf,s2,6);

    
    tcp_buf_data_ptr_move(&tcp_buf,8);
    sent_size=tcp_buf_copy_from_tcp_buf(&tcp_buf,s3,8);

    printf("%s %d %d\r\n",s3,sent_size,tcp_buf.used_size);

    return 0;
}