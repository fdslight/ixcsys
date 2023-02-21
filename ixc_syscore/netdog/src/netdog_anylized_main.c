#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>

#include <libgen.h>
#include <signal.h>
#include <execinfo.h>

#include "socket_server.h"
#include "netdog.h"
#include "anylize/anylize_worker.h"

#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/pfile.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];

static PyObject *py_anylize_ext=NULL;
static PyObject *py_anylize_inst=NULL;

/// 分配到的工作号
static int anylize_worker_no=0;

typedef struct{
    PyObject_HEAD
}anylizeObject;

static void
anylize_dealloc(anylizeObject *self)
{
    
}

static PyObject *
anylize_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    anylizeObject *self;
    self=(anylizeObject *)type->tp_alloc(type,0);
    if(NULL==self) return NULL;

    return (PyObject *)self;
}

static int
anylize_init(anylizeObject *self,PyObject *args,PyObject *kwds)
{
    return 0;
}

static PyObject *
anylize_worker_no_get(PyObject *self,PyObject *args)
{
    return PyLong_FromLong(anylize_worker_no);
}

static PyMemberDef anylize_members[]={
    {NULL}
};

static PyMethodDef anylize_methods[]={
    {"worker_no_get",(PyCFunction)anylize_worker_no_get,METH_NOARGS,"get worker no"},
    {NULL,NULL,0,NULL}
};

static PyTypeObject anylizeType={
    PyVarObject_HEAD_INIT(NULL,0)
    .tp_name="npkt_anylize.anylize",
    .tp_doc="python network anylize embed",
    .tp_basicsize=sizeof(anylizeObject),
    .tp_itemsize=0,
    .tp_flags=Py_TPFLAGS_DEFAULT,
    .tp_new=anylize_new,
    .tp_init=(initproc)anylize_init,
    .tp_dealloc=(destructor)anylize_dealloc,
    .tp_members=anylize_members,
    .tp_methods=anylize_methods
};

static struct PyModuleDef anylizeModule={
    PyModuleDef_HEAD_INIT,
    "npkt_anylize",
    NULL,
    -1,
    anylize_methods
};

static PyObject *
PyInit_anylize(void){
    PyObject *m;

    if(PyType_Ready(&anylizeType) < 0) return NULL;

    m=PyModule_Create(&anylizeModule);
    if(NULL==m) return NULL;

    Py_INCREF(&anylizeType);
    if(PyModule_AddObject(m,"npkt_anylize",(PyObject *)&anylizeType)<0){
        Py_DECREF(&anylizeType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}

static int ixc_init_python(int debug)
{
    PyObject *py_module=NULL,*cls,*v,*args,*pfunc;
    char py_module_dir[8192];

    sprintf(py_module_dir,"%s/../../",run_dir);
    
    PyImport_AppendInittab("netpkt_anylize", &PyInit_anylize);
    Py_Initialize();
   
    py_add_path(py_module_dir);

    // 加载Python路由助手模块
    py_module=py_module_load("ixc_syscore.netdog.anylize_helper");
    //PyErr_Print();

    if(NULL==py_module){
        PyErr_Print();
        STDERR("cannot load python anylize python module\r\n");
        return -1;
    }

    v=PyBool_FromLong(debug);
    args=Py_BuildValue("(N)",v);

    pfunc=PyObject_GetAttrString(py_module,"helper");
    cls=PyObject_CallObject(pfunc, args);
    if(NULL==cls){
        PyErr_Print();
        return -1;
    }

    py_anylize_ext=py_module;
    py_anylize_inst=cls;

    Py_XDECREF(pfunc);
    Py_XDECREF(args);

    return 0;
}

static int ixc_start_python(void)
{
    PyObject *pfunc,*result;

    pfunc=PyObject_GetAttrString(py_anylize_inst,"start");
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

static void ixc_python_release(void)
{
    PyObject *pfunc,*result;

    pfunc=PyObject_GetAttrString(py_anylize_inst,"release");
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

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
    wchar_t *program = Py_DecodeLocale(argv[0], NULL);

    sprintf(pid_path,"/tmp/ixcsys/netdog/netdog_anylized_%s.pid",argv[2]);

    if (realpath(argv[0], run_dir) == NULL)
    {
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }

    dirname(run_dir);
    Py_SetProgramName(program);
}

static void ixc_segfault_info()
{
    void *bufs[4096];
    char **strs;
    int nptrs;

    nptrs = backtrace(bufs, 4096);
    strs = backtrace_symbols(bufs, nptrs);
    if (NULL == strs)
        return;

    for (int n = 0; n < nptrs; n++)
    {
        fprintf(stderr, "%s\r\n", strs[n]);
    }

    free(strs);
    exit(EXIT_FAILURE);
}

static void netdog_stop(void)
{
    ixc_python_release();
    Py_Finalize();

    ixc_socket_server_uninit();
    ixc_anylize_worker_uninit();
    
    if(!access(pid_path,F_OK)) remove(pid_path);

    exit(EXIT_SUCCESS);
}

static void ixc_signal_handle(int signum)
{
    switch (signum)
    {
    case SIGINT:
        netdog_stop();
        break;
    case SIGSEGV:
        ixc_segfault_info();
        break;
    }
}

static void netdog_start(int is_debug)
{
    int rs;


    signal(SIGSEGV, ixc_signal_handle);
    signal(SIGINT, ixc_signal_handle);

    rs=ixc_anylize_worker_init();

    if(rs<0){
        STDERR("cannot init anylize worker\r\n");
        exit(EXIT_SUCCESS);
    }

    rs = ixc_socket_server_init();
    if (rs < 0)
    {
        STDERR("cannot init socket server\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_init_python(is_debug);
    if(rs<0){
        STDERR("cannot init python\r\n");
        exit(EXIT_SUCCESS);
    }
    rs=ixc_start_python();
    if(rs<0){
        exit(EXIT_SUCCESS);
    }

    
    pfile_write(pid_path, getpid());
    ixc_socket_server_ioloop();
}

static void send_int_sig(void)
{
    pid_t pid = pfile_read(pid_path);
    if (pid < 0)
        return;
    kill(pid, SIGINT);
}

int main(int argc, char *argv[])
{
    const char *helper = "start | stop | debug  process_seq";
    int rs;
    pid_t pid;

    if (argc != 3)
    {
        printf("%s\r\n", helper);
        return -1;
    }

    rs=atoi(argv[2]);

    if(rs<0){
        printf("wrong process_seq %s\r\n",argv[2]);
        return -1;
    }

    if(rs>95){
        printf("max process seq is 95\r\n");
        return -1;
    }

    ixc_set_run_env(argv);

    if(!access(pid_path,F_OK)){
        printf("error:anylize process %s exists\r\n",argv[2]);
        return -1;
    }
    
    anylize_worker_no=rs;

    if (!strcmp(argv[1], "start"))
    {
        pid = fork();
        if (pid != 0)
            exit(EXIT_SUCCESS);

        setsid();
        umask(0);

        pid = fork();
        if (pid != 0)
            exit(EXIT_SUCCESS);

        netdog_start(0);

        return 0;
    }

    if (!strcmp(argv[1], "stop"))
    {
        send_int_sig();
        return 0;
    }

    if (!strcmp(argv[1], "debug"))
    {
        netdog_start(1);
        return 0;
    }

    printf("%s\r\n", helper);

    return 0;
}