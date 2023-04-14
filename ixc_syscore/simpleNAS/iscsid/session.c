#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>

#include "session.h"
#include "iscsid.h"

#include "../../../pywind/clib/ev/ev.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/pycall.h"

static PyObject *py_helper_module=NULL;
static PyObject *py_helper_instance=NULL;

static struct ev_set ev_set;
static int session_fd=-1;
///循环更新事件
static time_t loop_time_up=0;
static unsigned char skt_addr[256];
static int is_ipv6_skt=0;

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

static int ixc_init_python(int debug)
{
    PyObject *py_module=NULL,*cls,*v,*args,*pfunc;
    char py_module_dir[8192];

    sprintf(py_module_dir,"%s/../../",ixc_iscsid_run_dir_get());
    
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

static void ixc_session_myloop(void)
{
    time_t now=time(NULL);

    sysloop_do();

    if(now-loop_time_up<30) return;

    // 每隔30s调用一次python循环
    loop_time_up=now;
    ixc_python_loop();
}

static int iscsi_session_readable_fn(struct ev *ev)
{
	ssize_t recv_size;
	int rs;

	return 0;
}

static int iscsi_session_writable_fn(struct ev *ev)
{
	return 0;
}

static int iscsi_session_timeout_fn(struct ev *ev)
{
	time_t now=time(NULL);

	return 0;
}

static int iscsi_session_del_fn(struct ev *ev)
{
	return 0;
}

int ixc_iscsi_session_create(int fd,void *sockaddr,socklen_t addrlen,int is_ipv6)
{
    int rs;
    struct ev *ev;
    char path[128];

    is_ipv6_skt=is_ipv6;
    session_fd=fd;

    memcpy(skt_addr,sockaddr,addrlen);

    ixc_iscsid_set_as_no_listener();

    loop_time_up=time(NULL);
    rs=ixc_init_python(ixc_iscsid_is_debug());

    if(rs<0){
        STDERR("cannot init python helper instance\r\n");
        exit(EXIT_FAILURE);
    }

    rs=ev_set_init(&ev_set,0);
    if(rs<0){
        STDERR("cannot init event\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=sysloop_init();
    if(rs<0){
        STDERR("cannot init sysloop\r\n");
        exit(EXIT_FAILURE);
    }

    ev_set.myloop_fn=ixc_session_myloop;
  
    if(ixc_start_python()<0){
        STDERR("cannot start python helper\r\n");
        exit(EXIT_SUCCESS);
    }

    ev=ev_create(&ev_set,fd);
    if(NULL==ev){
        STDERR("cannot create event file object\r\n");
        exit(EXIT_SUCCESS);
    }

    EV_INIT_SET(ev,iscsi_session_readable_fn,iscsi_session_writable_fn,iscsi_session_timeout_fn,iscsi_session_del_fn,NULL);
    
    rs=ev_setnonblocking(fd);

	if(rs<0){
		close(fd);
		STDERR("cannot set nonblocking\r\n");
		exit(EXIT_FAILURE);
	}

    sprintf(path,"/tmp/ixcsys/simpleNAS/iscsi.child.%d",getpid());

    ixc_iscsid_set_pid_path(path);

    ev_modify(&ev_set,ev,EV_READABLE,EV_CTL_ADD);
    ev_loop(&ev_set);
    
    return 0;
}

void ixc_iscsi_session_delete(void)
{
    const char *path=ixc_iscsid_get_pid_path();

    ixc_python_release();
    close(session_fd);

    remove(path);
}