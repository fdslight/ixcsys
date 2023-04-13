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

#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"
#include "../../../pywind/clib/pfile.h"
#include "../../../pywind/clib/sysloop.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];

static PyObject *py_helper_module=NULL;
static PyObject *py_helper_instance=NULL;

static struct ev_set ixc_ev_set;
///循环更新事件
static time_t loop_time_up=0;

typedef struct{
    PyObject_HEAD
}iscsiObject;

static void
iscsi_dealloc(iscsiObject *self)
{
    
}

static PyObject *
iscsi_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    iscsiObject *self;
    self=(iscsiObject *)type->tp_alloc(type,0);
    if(NULL==self) return NULL;

    return (PyObject *)self;
}

static int
iscsi_init(iscsiObject *self,PyObject *args,PyObject *kwds)
{
    return 0;
}

/// C语言LOG设置
static PyObject *
iscsi_clog_set(PyObject *self,PyObject *args)
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


static PyMemberDef iscsi_members[]={
    {NULL}
};

static PyMethodDef iscsiMethods[]={
    //
    {"clog_set",(PyCFunction)iscsi_clog_set,METH_VARARGS,"set c language log path"},
    //

    {NULL,NULL,0,NULL}
};

static PyTypeObject iscsiType={
    PyVarObject_HEAD_INIT(NULL,0)
    .tp_name="iscsi.iscsi",
    .tp_doc="python iscsi library",
    .tp_basicsize=sizeof(iscsiObject),
    .tp_itemsize=0,
    .tp_flags=Py_TPFLAGS_DEFAULT,
    .tp_new=iscsi_new,
    .tp_init=(initproc)iscsi_init,
    .tp_dealloc=(destructor)iscsi_dealloc,
    .tp_members=iscsi_members,
    .tp_methods=iscsiMethods
};

static struct PyModuleDef iscsiModule={
    PyModuleDef_HEAD_INIT,
    "iscsi",
    NULL,
    -1,
    iscsiMethods
};

static PyObject *
PyInit_iscsi(void){
    PyObject *m;

    if(PyType_Ready(&iscsiType) < 0) return NULL;

    m=PyModule_Create(&iscsiModule);
    if(NULL==m) return NULL;

    Py_INCREF(&iscsiType);
    if(PyModule_AddObject(m,"iscsi",(PyObject *)&iscsiType)<0){
        Py_DECREF(&iscsiType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}

static void ixc_exit(void);

void ixc_iscsi_exit(void)
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
    wchar_t *program = Py_DecodeLocale(argv[0], NULL);
    strcpy(pid_path,"/tmp/ixcsys/simpleNAS/iscsid.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);

    Py_SetProgramName(program);
}

static int ixc_init_python(int debug)
{
    PyObject *py_module=NULL,*cls,*v,*args,*pfunc;
    char py_module_dir[8192];

    sprintf(py_module_dir,"%s/../../",run_dir);
    
    PyImport_AppendInittab("iscsi", &PyInit_iscsi);
    Py_Initialize();

    py_add_path(py_module_dir);

    // 加载Python路由助手模块
    py_module=py_module_load("ixc_syscore.simpleNAS.__helper");
    //PyErr_Print();

    if(NULL==py_module){
        PyErr_Print();
        STDERR("cannot load python iscsi __helper module\r\n");
        return -1;
    }

    v=PyBool_FromLong(debug);
    args=Py_BuildValue("(N)",v);

    pfunc=PyObject_GetAttrString(py_module,"helper");
    if(NULL==pfunc){
        PyErr_Print();
        STDERR("cannot found function helper\r\n");
        return -1;
    }

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

    sysloop_do();

    if(now-loop_time_up<30) return;

    // 每隔30s调用一次python循环
    loop_time_up=now;
    ixc_python_loop();
}


static void ixc_start(int debug)
{
    int rs;

    if(!access(pid_path,F_OK)){
        STDERR("process ixc_iscsid exists\r\n");
        return;
    }

    loop_time_up=time(NULL);

    signal(SIGSEGV,ixc_signal_handle);
    signal(SIGINT,ixc_signal_handle);

    // 注意这里需要最初初始化以便检查环境
    rs=ixc_init_python(debug);
    if(rs<0){
        STDERR("cannot init python helper instance\r\n");
        exit(EXIT_SUCCESS);
    }

     rs=ev_set_init(&ixc_ev_set,0);
    if(rs<0){
        STDERR("cannot init event\r\n");
        exit(EXIT_SUCCESS);
    }

    ixc_ev_set.myloop_fn=ixc_myloop;
  
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
        ixc_stop();
        return 0;
    }

    if(!strcmp(argv[1],"debug")){
        ixc_start(1);
        return 0;
    }

    printf("%s\r\n",helper);
    return -1;
}
