#include<getopt.h>
#include<string.h>
#include<unistd.h>
#include<fcntl.h>
#include<sys/stat.h>

#include "../../clib/debug.h"

/// @发送停止web服务器信号
/// @param path 
static void send_stop_web_sig(const char *path)
{
    struct stat s_buf;
    
    if(access(path,F_OK)){
        printf("ERROR:not found pid file %s\r\n",path);
        return;
    }

    stat(path,&s_buf);

    if(S_ISDIR(s_buf.st_mode)){
        printf("ERROR:%s is a directory\r\n",path);
        return;
    }
}

int main(int argc,char *argv[])
{
    const char *help_doc="\
start --webroot=webroot --scgi-socket-path=scgi-socket-path [--pid-file=pid-path]\r\n\
stop process-pid-file \
    ";
    
    if(argc<3){
        printf("%s\r\n",help_doc);
        return -1;
    }

    if(strcmp(argv[1],"start") && strcmp(argv[1],"stop")){
        printf("%s\r\n",help_doc);
        return -1;
    }

    if(!strcmp(argv[1],"stop")){
        send_stop_web_sig(argv[2]);
        return 0;
    }
    
    return 0;
}