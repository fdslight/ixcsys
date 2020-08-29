#define  PY_SSIZE_T_CLEAN

#include<Python.h>
#include<structmember.h>

#include "../src/mbuf.h"
#include "../src/router.h"
#include "../src/netif.h"


typedef struct{
    PyObject_HEAD
}routerObject;

static PyObject *router_sent_cb=NULL;
static PyObject *router_write_ev_tell_cb=NULL;

int ixc_router_send(void *buf,size_t size,int flags)
{
    if(NULL==router_sent_cb) return -1;

    return 0;
}

static void
router_dealloc(routerObject *self)
{

}

static PyObject *
router_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    return NULL;
}

static int
router_init(routerObject *self,PyObject *args,PyObject *kwds)
{
    return 0;
}

/// 是否需要等待,如果有需要待发送的数据包等内容,那么就不能等待
static PyObject *
router_iowait(PyObject *self,PyObject *args)
{
    return NULL;
}

static PyObject *
router_myloop(PyObject *self,PyObject *args)
{
    return NULL;
}

static PyObject *
router_netif_create(PyObject *self,PyObject *args)
{
    return NULL;
}

static PyObject *
router_netif_delete(PyObject *self,PyObject *args)
{
    return NULL;
}


static PyMemberDef router_members[]={
    {NULL}
};

static PyMethodDef routerMethods[]={
    {"iowait",(PyCFunction)router_iowait,METH_VARARGS,"tell if wait"},
    {"myloop",(PyCFunction)router_myloop,METH_VARARGS,"loop call"},
    {"netif_create",(PyCFunction)router_netif_create,METH_VARARGS,"create tap device"},
    {"netif_delete",(PyCFunction)router_netif_delete,METH_VARARGS,"delete tap device"},
    {NULL,NULL,0,NULL}
};

static PyTypeObject routerType={
    PyVarObject_HEAD_INIT(NULL,0)
    .tp_name="router.router",
    .tp_doc="python router library",
    .tp_basicsize=sizeof(routerObject),
    .tp_itemsize=0,
    .tp_flags=Py_TPFLAGS_DEFAULT,
    .tp_new=router_new,
    .tp_init=(initproc)router_init,
    .tp_dealloc=(destructor)router_dealloc,
    .tp_members=router_members,
    .tp_methods=routerMethods
};

static struct PyModuleDef routerModule={
    PyModuleDef_HEAD_INIT,
    "router",
    NULL,
    -1,
    routerMethods
};

PyMODINIT_FUNC
PyInit_router(void){
    PyObject *m;

    if(PyType_Ready(&routerType) < 0) return NULL;

    m=PyModule_Create(&routerModule);
    if(NULL==m) return NULL;

    Py_INCREF(&routerType);
    if(PyModule_AddObject(m,"router",(PyObject *)&routerType)<0){
        Py_DECREF(&routerType);
        Py_DECREF(m);
        return NULL;
    }


    return m;
}