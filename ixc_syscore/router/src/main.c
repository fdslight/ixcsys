#include<unistd.h>
#include<signal.h>
#include<stdlib.h>
#include<execinfo.h>
#include<libgen.h>

#define  PY_SSIZE_T_CLEAN

#include "mbuf.h"
#include "router.h"
#include "netif.h"
#include "addr_map.h"
#include "qos.h"
#include "route.h"
#include "src_filter.h"
#include "ether.h"
#include "ip.h"
#include "ip6.h"
#include "nat.h"
#include "pppoe.h"
#include "ipunfrag.h"
#include "debug.h"
#include "ip6sec.h"
#include "port_map.h"
#include "global.h"
#include "vswitch.h"


#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"
#include "../../../pywind/clib/ev/rpc.h"
#include "../../../pywind/clib/pfile.h"
#include "../../../pywind/clib/sysloop.h"

/// 进程文件路径
static char pid_path[1024];
/// 运行目录
static char run_dir[1024];

static PyObject *py_helper_module=NULL;
static PyObject *py_helper_instance=NULL;

static struct ev_set ixc_ev_set;

static void ixc_segfault_info()
{
    void *bufs[4096];
    char **strs;
    int nptrs;

    nptrs=backtrace(bufs,4096);
    strs=backtrace_symbols(bufs,nptrs);
    if(NULL==strs) return;

    for(int n=0;n<nptrs;n++){
        fprintf(stderr,"%s\r\n",strs[n]);
    }
    free(strs);
    exit(EXIT_FAILURE);
}

static void ixc_stop_from_sig(void)
{

    Py_Finalize();
}

static void ixc_signal_handle(int signum)
{
    switch(signum){
        case SIGINT:
            ixc_stop_from_sig();
            break;
        case SIGSEGV:
            ixc_segfault_info();
            break;
    }
}

static int ixc_rpc_fn_req(const char *name,void *arg,unsigned short arg_size,void *result,unsigned short *res_size)
{
    PyObject *res=NULL,*pfunc,*args;
    int is_error;
    Py_ssize_t size;
    const char *data;

    args=Py_BuildValue("(sy#)",name,arg,arg_size);

    pfunc=PyObject_GetAttrString(py_helper_instance,"rpc_fn_call");
    res=PyObject_CallObject(pfunc, args);

    if(NULL==res){
        Py_XDECREF(pfunc);
        sprintf(result,"system error for call function %s",name);
        *res_size=strlen(result);
        return RPC_ERR_OTHER;
    }
    // 此处解析Python调用结果
    PyArg_ParseTuple(res,"iy#",&is_error,&data,&size);
    *res_size=size;
    memcpy(result,data,*res_size);

    Py_XDECREF(pfunc);
    Py_XDECREF(args);
    Py_XDECREF(res);

    return is_error;
}

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
    wchar_t *program = Py_DecodeLocale(argv[0], NULL);

    strcpy(pid_path,"/tmp/ixcsys/router/router_core.pid");
    realpath(argv[0],run_dir);
    dirname(run_dir);

    Py_SetProgramName(program);
}

static int ixc_start_python(void)
{
    PyObject *py_module=NULL,*cls,*args,*pfunc;
    char py_module_dir[2048];

    sprintf(py_module_dir,"%s/../../",run_dir);

    Py_Initialize();

    py_add_path("/home/mk/ixcsys");
   
    // 加载Python路由助手模块
    py_module=py_module_load("ixc_syscore.router._ixc_router_helper");

    if(NULL==py_module){
        STDERR("cannot load python route_helper module\r\n");
        return -1;
    }

    pfunc=PyObject_GetAttrString(py_module,"helper");
    cls=PyObject_CallObject(pfunc, NULL);

    py_helper_module=py_module;
    py_helper_instance=cls;

    Py_XDECREF(pfunc);
    // 把C扩展模块加入到Python模块表中
    //PyImport_AppendInittab("router",&PyInit_router);

    return 0;
}

static void ixc_start(int debug)
{
    int rs;

    signal(SIGSEGV,ixc_signal_handle);
    signal(SIGINT,ixc_signal_handle);

    rs=ev_set_init(&ixc_ev_set,0);
    if(rs<0){
        STDERR("cannot init event\r\n");
        return;
    }

    rs=sysloop_init();
    if(rs<0){
        STDERR("cannot init sysloop\r\n");
        return;
    }

    rs=ixc_g_init();
    if(rs<0){
        STDERR("cannot init global\r\n");
        return;
    }

    rs=ixc_vsw_init();
    if(rs<0){
        STDERR("cannot init vswitch\r\n");
        return;
    }

    rs=ixc_mbuf_init(512);
    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        return;
    }

    rs=ixc_port_map_init();
    if(rs<0){
        STDERR("cannot init port_map\r\n");
        return;
    }

    rs=ixc_ip6sec_init();
    if(rs<0){
        STDERR("cannot init ip6sec\r\n");
        return;
    }

    rs=ixc_nat_init();
    if(rs<0){
        STDERR("cannot init nat\r\n");
        return;
    }

    rs=ixc_netif_init(&ixc_ev_set);
    if(rs<0){
        STDERR("cannot init netif\r\n");
        return;
    }

    rs=ixc_addr_map_init();
    if(rs<0){
        STDERR("cannot init addr map\r\n");
        return;
    }

    rs=ixc_qos_init();
    if(rs<0){
        STDERR("cannot init qos\r\n");
        return;
    }

    rs=ixc_route_init();
    if(rs<0){
        STDERR("cannot init route\r\n");
        return;
    }

    rs=ixc_src_filter_init();
    if(rs<0){
        STDERR("cannot init P2P\r\n");
        return;
    }

    rs=ixc_pppoe_init();
    if(rs<0){
        STDERR("cannot init pppoe\r\n");
        return;
    }

    rs=ixc_ip6_init();
    if(rs<0){
        STDERR("cannot init ICMPv6\r\n");
        return;
    }

    rs=ixc_ipunfrag_init();
    if(rs<0){
        STDERR("cannot init ipunfrag\r\n");
        return;
    }

    rs=rpc_create(&ixc_ev_set,"127.0.0.1",1999,0,ixc_rpc_fn_req);
    if(rs<0){
        STDERR("cannot create rpc\r\n");
        return;
    }

    ixc_start_python();
}

static void ixc_stop(void)
{
    pid_t pid=pfile_read(pid_path);

    if(pid<0) return;
    
    kill(pid,SIGINT);
}

int main(int argc,char *argv[])
{
    const char *helper="start | stop | debug";
    pid_t pid;

    if(argc!=2){
        printf("%s\r\n",helper);
        return -1;
    }

    ixc_set_run_env(argv);

    if(!strcmp(argv[1],"start")){
        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        setsid();
        umask(0);

        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        ixc_start(0);

        return 0;
    }

    if(!strcmp(argv[1],"stop")){
        return 0;
    }

    if(!strcmp(argv[1],"debug")){
        ixc_start(1);
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;
}