
#include "../../clib/debug.h"


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

    



    
    return 0;
}