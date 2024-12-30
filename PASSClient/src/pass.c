#include<unistd.h>
#include<signal.h>
#include<stdlib.h>
#include<execinfo.h>
#include<libgen.h>
#include<time.h>

#include<sched.h>

#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>

#include "mbuf.h"
#include "netif.h"
#include "npfwd.h"

#include "../../pywind/clib/pycall.h"
#include "../../pywind/clib/debug.h"
#include "../../pywind/clib/ev/ev.h"
#include "../../pywind/clib/pfile.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];

/// 路由器运行开始时间
static time_t run_start_time=0;

static PyObject *py_helper_module=NULL;
static PyObject *py_helper_instance=NULL;

static struct ev_set ixc_ev_set;
///循环更新事件
static time_t loop_time_up=0;

typedef struct{
    PyObject_HEAD
}passObject;

static void
pass_dealloc(passObject *self)
{
    
}

static PyObject *
pass_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    passObject *self;
    self=(passObject *)type->tp_alloc(type,0);
    if(NULL==self) return NULL;

    return (PyObject *)self;
}

static int
pass_init(passObject *self,PyObject *args,PyObject *kwds)
{
    return 0;
}

static PyObject *
pass_netif_create(PyObject *self,PyObject *args)
{
    const char *name;
    int fd;

    if(!PyArg_ParseTuple(args,"s",&name)) return NULL;
    fd=ixc_netif_create(name);

    return PyLong_FromLong(fd);
}

static PyObject *
pass_netif_delete(PyObject *self,PyObject *args)
{
    ixc_netif_delete();

    Py_RETURN_NONE;
}


/// C语言LOG设置
static PyObject *
pass_clog_set(PyObject *self,PyObject *args)
{
    const char *stdout_path,*stderr_path;

    if(!PyArg_ParseTuple(args,"ss",&stdout_path,&stderr_path)) return NULL;

    if(freopen(stdout_path,"a+",stdout)==NULL){
        STDERR("cannot set stdout\r\n");
        return NULL;
    }

    if(freopen(stderr_path,"a+",stderr)==NULL){
        STDERR("cannot set stderr\r\n");
        return NULL;
    }

    Py_RETURN_NONE;
}

/// 设置重定向
static PyObject *
pass_netpkt_forward_set(PyObject *self,PyObject *args)
{
    unsigned char *key;
    unsigned char *address;
    Py_ssize_t key_size;
    Py_ssize_t addr_len;
    unsigned short port;
    int rs;

    if(!PyArg_ParseTuple(args,"y#y#H",&key,&key_size,&address,&addr_len,&port)) return NULL;

    if(key_size!=16){
        Py_RETURN_FALSE;
    }

    if(addr_len!=4){
        Py_RETURN_FALSE;
    }

    rs=ixc_npfwd_set_forward(key,address,port);
    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
pass_cpu_num(PyObject *self,PyObject *args)
{
    int cpus=sysconf(_SC_NPROCESSORS_ONLN);

    return PyLong_FromLong(cpus);
}


/// 绑定进程到指定CPU,避免CPU上下文切换
static PyObject *
pass_bind_cpu(PyObject *self,PyObject *args)
{
	int cpus=sysconf(_SC_NPROCESSORS_ONLN);
    int cpu_no=0;

    cpu_set_t mask;

    if(!PyArg_ParseTuple(args,"i",&cpu_no)) return NULL;

    CPU_ZERO(&mask);
	
    if(cpus<=cpu_no){
        STDERR("cannot bind cpu %d,not found cpu\r\n",cpu_no);
        Py_RETURN_FALSE;
    }

    if(cpu_no<0){
        for(int n=0;n<cpus;n++){
            CPU_ZERO(&mask);
            CPU_CLR(n,&mask);
            sched_setaffinity(0,sizeof(cpu_set_t),&mask);
        }
        Py_RETURN_TRUE;
    }

    CPU_SET(cpu_no,&mask);

    if(sched_setaffinity(0,sizeof(cpu_set_t),&mask)==-1){
        STDERR("cannot bind to cpu %d\r\n",cpu_no);
        Py_RETURN_FALSE;
    }
	usleep(1000);
    Py_RETURN_TRUE;
}

/// 获取运行开始时间
static PyObject *
pass_start_time(PyObject *self,PyObject *args)
{
    return PyLong_FromUnsignedLongLong(run_start_time);
}


static PyMemberDef pass_members[]={
    {NULL}
};

static PyMethodDef passMethods[]={
    {"netif_create",(PyCFunction)pass_netif_create,METH_VARARGS,"create tap device"},
    {"netif_delete",(PyCFunction)pass_netif_delete,METH_VARARGS,"delete tap device"},
    {"clog_set",(PyCFunction)pass_clog_set,METH_VARARGS,"set c language log path"},
    {"cpu_num",(PyCFunction)pass_cpu_num,METH_NOARGS,"get cpu num"},
    {"bind_cpu",(PyCFunction)pass_bind_cpu,METH_VARARGS,"bind process to cpu core"},
    {"netpkt_forward_set",(PyCFunction)pass_netpkt_forward_set,METH_VARARGS,"netpkt forward set"},
    //
    {"pass_start_time",(PyCFunction)pass_start_time,METH_NOARGS,"get pass start time"},
    //

    {NULL,NULL,0,NULL}
};

static PyTypeObject passType={
    PyVarObject_HEAD_INIT(NULL,0)
    .tp_name="PASSClientRuntime.PASSClientRuntime",
    .tp_doc="python PASSClient library",
    .tp_basicsize=sizeof(passObject),
    .tp_itemsize=0,
    .tp_flags=Py_TPFLAGS_DEFAULT,
    .tp_new=pass_new,
    .tp_init=(initproc)pass_init,
    .tp_dealloc=(destructor)pass_dealloc,
    .tp_members=pass_members,
    .tp_methods=passMethods
};

static struct PyModuleDef passModule={
    PyModuleDef_HEAD_INIT,
    "PASSClientRuntime",
    NULL,
    -1,
    passMethods
};

static PyObject *
PyInit_PASSClientRuntime(void){
    PyObject *m;

    if(PyType_Ready(&passType) < 0) return NULL;

    m=PyModule_Create(&passModule);
    if(NULL==m) return NULL;

    Py_INCREF(&passType);
    if(PyModule_AddObject(m,"PASSClientRuntime",(PyObject *)&passType)<0){
        Py_DECREF(&passType);
        Py_DECREF(m);
        return NULL;
    }
    return m;
}

static void ixc_exit(void);


void ixc_pass_exit(void)
{
    ixc_exit();
}


static void ixc_python_loop(void)
{
    PyObject *pfunc,*result;

    pfunc=PyObject_GetAttrString(py_helper_instance,"loop");
    if(NULL==pfunc){
        DBG("cannot found python function loop\r\n");
        return;
    }

    result=PyObject_CallObject(pfunc, NULL);

    if(NULL==result){
        PyErr_Print();
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(result);

    return;
}


static void ixc_python_release(void)
{
    PyObject *pfunc,*result;

    pfunc=PyObject_GetAttrString(py_helper_instance,"release");
    if(NULL==pfunc){
        DBG("cannot found python function release\r\n");
        return;
    }

    result=PyObject_CallObject(pfunc, NULL);

    if(NULL==result){
        PyErr_Print();
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(result);
}

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

static void ixc_exit(void)
{
    if(NULL!=py_helper_instance){
        ixc_python_release();
        Py_Finalize();
    }
    ixc_npfwd_uninit();
    ixc_netif_uninit();
    
    exit(EXIT_SUCCESS);
}

static void ixc_signal_handle(int signum)
{
    switch(signum){
        case SIGINT:
            ixc_exit();
            break;
        case SIGSEGV:
            ixc_segfault_info();
            break;
    }
}

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
    //wchar_t *program = Py_DecodeLocale(argv[0], NULL);

    strcpy(pid_path,"ixc_pass.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);
/*
#if PY_MINOR_VERSION >= 11
    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.program_name=program;
#else
    Py_SetProgramName(program);
#endif**/
}

static int ixc_init_python(int debug,char *argv[])
{
    PyObject *py_module=NULL,*cls,*v,*args,*pfunc;
    char py_module_dir[8192];

    sprintf(py_module_dir,"%s",run_dir);
    
    PyImport_AppendInittab("PASSClientRuntime", &PyInit_PASSClientRuntime);
    Py_Initialize();
   
    py_add_path(py_module_dir);

    // 加载模块
    py_module=py_module_load("PASSHelper");
    //PyErr_Print();

    if(NULL==py_module){
        PyErr_Print();
        STDERR("cannot load python route_helper module\r\n");
        return -1;
    }

    v=PyBool_FromLong(debug);
    args=Py_BuildValue("(Nssss)",v,argv[2],argv[3],argv[4],argv[5]);

    pfunc=PyObject_GetAttrString(py_module,"helper");
    cls=PyObject_CallObject(pfunc, args);

    if(NULL==cls){
        PyErr_Print();
        return -1;
    }

    py_helper_module=py_module;
    py_helper_instance=cls;

    Py_XDECREF(pfunc);
    Py_XDECREF(args);

    return 0;
}

static int ixc_start_python(void)
{
    PyObject *pfunc,*result;

    pfunc=PyObject_GetAttrString(py_helper_instance,"start");
    if(NULL==pfunc){
        DBG("cannot found python function start\r\n");
        return -1;
    }

    result=PyObject_CallObject(pfunc, NULL);

    if(NULL==result){
        PyErr_Print();
        return -1;
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(result);

    return 0;
}

static void ixc_myloop(void)
{
    time_t now=time(NULL);

    ixc_ev_set.wait_timeout=10;
    
    if(now-loop_time_up<30) return;

    // 每隔30s调用一次python循环
    loop_time_up=now;
    ixc_python_loop();
}


static void ixc_start(int debug,char *argv[])
{
    int rs;
    int port=atoi(argv[3]);
    if(port<1 || port >= 0xffff){
        printf("ERRROR:wrong port number %s",argv[3]);
        exit(-1);
    }

    if(!access(pid_path,F_OK)){
        STDERR("process ixc_pass_core exists\r\n");
        return;
    }

    loop_time_up=time(NULL);

    signal(SIGSEGV,ixc_signal_handle);
    signal(SIGINT,ixc_signal_handle);

    run_start_time=time(NULL);

    // 注意这里需要最初初始化以便检查环境
    rs=ixc_init_python(debug,argv);
    if(rs<0){
        STDERR("cannot init python helper instance\r\n");
        exit(EXIT_SUCCESS);
    }

    if(rs<0){
       ixc_netif_uninit();
       STDERR("cannot start python\r\n");
       exit(EXIT_SUCCESS);
    }

    rs=ev_set_init(&ixc_ev_set,0);
    if(rs<0){
        STDERR("cannot init event\r\n");
        exit(EXIT_SUCCESS);
    }

    ixc_ev_set.myloop_fn=ixc_myloop;

    rs=ixc_mbuf_init(1024);
    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_npfwd_init(&ixc_ev_set);
    if(rs<0){
        STDERR("cannot init npfwd\r\n");
        exit(EXIT_SUCCESS);
    }
    
    rs=ixc_netif_init(&ixc_ev_set);
    if(rs<0){
        STDERR("cannot init netif\r\n");
        exit(EXIT_SUCCESS);
    }
  
    if(ixc_start_python()<0){
        STDERR("cannot start python helper\r\n");
        exit(EXIT_SUCCESS);
    }

    if(!debug) pfile_write(pid_path,getpid());
    
    ev_loop(&ixc_ev_set);
}

static void ixc_stop(void)
{
    pid_t pid=pfile_read(pid_path);

    if(pid<0) return;
    if(!access(pid_path,F_OK)) remove(pid_path);

    kill(pid,SIGINT);
}

int main(int argc,char *argv[])
{
    const char *helper="start | stop | debug NICName LocalPort Host Key";
    pid_t pid;

    if(argc<2){
        printf("%s\r\n",helper);
        return -1;  
    }


    ixc_set_run_env(argv);

    if(!strcmp(argv[1],"start")){
        if(argc!=6){
            printf("%s\r\n",helper);
            return -1;
        }

        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        setsid();
        umask(0);

        pid=fork();
        if(pid!=0) exit(EXIT_SUCCESS);

        ixc_start(0,argv);

        return 0;
    }

    if(!strcmp(argv[1],"stop")){
        ixc_stop();
        return 0;
    }

    if(!strcmp(argv[1],"debug")){
        if(argc!=6){
            printf("%s\r\n",helper);
            return -1;
        }
        ixc_start(1,argv);
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;
}
