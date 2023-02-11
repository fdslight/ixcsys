

#include "session.h"
#include "../iscsid.h"
#include "../net_worker.h"

#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>

#include "../../../../pywind/clib/pycall.h"

static PyObject *py_helper_module=NULL;
static PyObject *py_helper_instance=NULL;

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

PyObject *iscsi_send(PyObject *self,PyObject *args)
{
    const char *data;
    Py_ssize_t size;

    if(!PyArg_ParseTuple(args,"y#",&data,&size)) return NULL;

    Py_RETURN_NONE;
}

PyObject *iscsi_close(PyObject *self,PyObject *args)
{
    ixc_net_worker_close();

    Py_RETURN_NONE;
}

static PyMemberDef iscsi_members[]={
    {NULL}
};

static PyMethodDef iscsi_methods[]={
    {"send",(PyCFunction)iscsi_send,METH_VARARGS,"send iscsi data"},
    {"close",(PyCFunction)iscsi_close,METH_NOARGS,"close iscsi connection"},
    
    {NULL,NULL,0,NULL}
};

static PyTypeObject iscsiType={
    PyVarObject_HEAD_INIT(NULL,0)
    .tp_name="router.router",
    .tp_doc="python router library",
    .tp_basicsize=sizeof(iscsiObject),
    .tp_itemsize=0,
    .tp_flags=Py_TPFLAGS_DEFAULT,
    .tp_new=iscsi_new,
    .tp_init=(initproc)iscsi_init,
    .tp_dealloc=(destructor)iscsi_dealloc,
    .tp_members=iscsi_members,
    .tp_methods=iscsi_methods
};

static struct PyModuleDef iscsi_module={
    PyModuleDef_HEAD_INIT,
    "iscsi",
    NULL,
    -1,
    iscsi_methods
};

static PyObject *
PyInit_iscsi(void){
    PyObject *m;

    if(PyType_Ready(&iscsiType) < 0) return NULL;

    m=PyModule_Create(&iscsi_module);
    if(NULL==m) return NULL;

    Py_INCREF(&iscsiType);
    if(PyModule_AddObject(m,"router",(PyObject *)&iscsiType)<0){
        Py_DECREF(&iscsiType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}


static int ixc_init_python(int debug)
{
    const char *run_dir=ixc_iscsid_get_run_dir();
    PyObject *py_module=NULL,*cls,*v,*args,*pfunc;
    char py_module_dir[8192];

    sprintf(py_module_dir,"%s/../../",run_dir);
    //STDOUT("%s\r\n",py_module_dir);
    
    PyImport_AppendInittab("iscsi", &PyInit_iscsi);
    Py_Initialize();
   
    py_add_path(py_module_dir);

    // 加载Python路由助手模块
    py_module=py_module_load("ixc_syscore.iscsid.iscsi_helper");
    //PyErr_Print();

    if(NULL==py_module){
        PyErr_Print();
        STDERR("cannot load python iscsi_helper module\r\n");
        return -1;
    }

    v=PyBool_FromLong(debug);
    args=Py_BuildValue("(N)",v);

    pfunc=PyObject_GetAttrString(py_module,"helper");
    cls=PyObject_CallObject(pfunc, args);

    py_helper_module=py_module;
    py_helper_instance=cls;

    Py_XDECREF(pfunc);
    Py_XDECREF(args);

    return 0;
}

/// 发送数据到Python
static int ixc_iscsi_send_to_py(unsigned char *buf,size_t data_size)
{
    PyObject *pfunc,*result,*args;

    pfunc=PyObject_GetAttrString(py_helper_instance,"handle_data");
    if(NULL==pfunc){
        DBG("cannot found python function tell\r\n");
        return -1;
    }

    args=Py_BuildValue("(y#)",buf,data_size);
    result=PyObject_CallObject(pfunc, args);

    if(NULL==result){
        PyErr_Print();
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(args);
    Py_XDECREF(result);

    return 0;
}

int ixc_iscsi_session_init(void)
{
    int is_err=ixc_init_python(0);

    return is_err;
}

int ixc_iscsi_session_handle_request(struct ixc_mbuf *m)
{
    ixc_iscsi_send_to_py(m->data+m->begin,m->end-m->begin);
    ixc_mbuf_put(m);

    return 0;
}

void ixc_iscsi_session_uninit(void)
{

}