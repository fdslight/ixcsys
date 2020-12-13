#define  PY_SSIZE_T_CLEAN

#include<Python.h>
#include<structmember.h>
#include<execinfo.h>
#include<signal.h>

#include "../src/mbuf.h"
#include "../src/debug.h"

#include "../../../pywind/clib/sysloop.h"

typedef struct{
    PyObject_HEAD
}proxy_helper_object;

static PyObject *tcp_cb=NULL;
static PyObject *udp_cb=NULL;

static void ixc_segfault_handle(int signum)
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

static void
proxy_helper_dealloc(proxy_helper_object *self)
{
    mbuf_uninit();
}

static PyObject *
proxy_helper_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    proxy_helper_object *self;
    int rs=0;
    self=(proxy_helper_object *)type->tp_alloc(type,0);
    if(NULL==self) return NULL;

    rs=mbuf_init(1024);
    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        return NULL;
    }

    rs=sysloop_init();
    if(rs<0){
        STDERR("cannot init sysloop\r\n");
        return NULL;
    }

    signal(SIGSEGV,ixc_segfault_handle);

    return (PyObject *)self;
}

static int
proxy_helper_init(proxy_helper_object *self,PyObject *args,PyObject *kwds)
{
    PyObject *fn_tcp_cb,*fn_udp_cb;

    if(!PyArg_ParseTuple(args,"OO",&fn_tcp_cb,&fn_udp_cb)) return -1;
    if(!PyCallable_Check(fn_tcp_cb)){
        PyErr_SetString(PyExc_TypeError,"tcp callback function  must be callable");
        return -1;
    }
    if(!PyCallable_Check(fn_udp_cb)){
        PyErr_SetString(PyExc_TypeError,"ucp callback function  must be callable");
        return -1;
    }

    Py_XDECREF(tcp_cb);
    Py_XDECREF(udp_cb);

    tcp_cb=fn_tcp_cb;
    udp_cb=fn_udp_cb;

    Py_INCREF(tcp_cb);
    Py_INCREF(udp_cb);

    return 0;
}

static PyObject *
proxy_helper_myloop(PyObject *self,PyObject *args)
{
    sysloop_do();
    Py_RETURN_NONE;
}

static PyMemberDef proxy_helper_members[]={
    {NULL}
};

static PyMethodDef proxy_helper_methods[]={
    {"myloop",(PyCFunction)proxy_helper_myloop,METH_VARARGS,"loop call"},
    {NULL,NULL,0,NULL}
};

static PyTypeObject proxy_helper_type={
    PyVarObject_HEAD_INIT(NULL,0)
    .tp_name="proxy_helper.proxy_helper",
    .tp_doc="python proxy helper library",
    .tp_basicsize=sizeof(proxy_helper_object),
    .tp_itemsize=0,
    .tp_flags=Py_TPFLAGS_DEFAULT,
    .tp_new=proxy_helper_new,
    .tp_init=(initproc)proxy_helper_init,
    .tp_dealloc=(destructor)proxy_helper_dealloc,
    .tp_members=proxy_helper_members,
    .tp_methods=proxy_helper_methods
};

static struct PyModuleDef proxy_helper_module={
    PyModuleDef_HEAD_INIT,
    "proxy_helper",
    NULL,
    -1,
    proxy_helper_methods
};

PyMODINIT_FUNC
PyInit_proxy_helper(void){
    PyObject *m;

    if(PyType_Ready(&proxy_helper_type) < 0) return NULL;

    m=PyModule_Create(&proxy_helper_module);
    if(NULL==m) return NULL;

    Py_INCREF(&proxy_helper_type);
    if(PyModule_AddObject(m,"proxy_helper",(PyObject *)&proxy_helper_type)<0){
        Py_DECREF(&proxy_helper_type);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}