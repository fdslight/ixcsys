#define  PY_SSIZE_T_CLEAN

#include<Python.h>
#include<structmember.h>

#include "../src/mbuf.h"
#include "../src/router.h"
#include "../src/netif.h"
#include "../src/addr_map.h"
#include "../src/qos.h"
#include "../src/route.h"
#include "../src/p2p.h"
#include "../src/vpn.h"
#include "../src/dhcp_client.h"

#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/sysloop.h"

typedef struct{
    PyObject_HEAD
}routerObject;

static PyObject *router_sent_cb=NULL;
static PyObject *router_write_ev_tell_cb=NULL;

int ixc_router_send(void *buf,size_t size,int flags)
{
    PyObject *arglist,*result;
    if(NULL==router_sent_cb) return -1;

    arglist=Py_BuildValue("(y#i)",buf,size,flags);
    result=PyObject_CallObject(router_sent_cb,arglist);

    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0;
}

int ixc_router_write_ev_tell(int fd,int flags)
{
    PyObject *arglist,*result;
    if(NULL==router_write_ev_tell_cb) return -1;

    arglist=Py_BuildValue("(ii)",fd,flags);
    result=PyObject_CallObject(router_write_ev_tell_cb,arglist);

    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0;
}

static void
router_dealloc(routerObject *self)
{
    ixc_mbuf_uninit();
}

static PyObject *
router_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    routerObject *self;
    int rs=0;
    self=(routerObject *)type->tp_alloc(type,0);
    if(NULL==self) return NULL;

    rs=sysloop_init();
    if(rs<0){
        STDERR("cannot init sysloop\r\n");
        return NULL;
    }

    rs=ixc_mbuf_init(512);
    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        return NULL;
    }

    rs=ixc_netif_init();
    if(rs<0){
        STDERR("cannot init netif\r\n");
        return NULL;
    }

    rs=ixc_addr_map_init();
    if(rs<0){
        STDERR("cannot init addr map\r\n");
        return NULL;
    }

    rs=ixc_qos_init();
    if(rs<0){
        STDERR("cannot init qos\r\n");
        return NULL;
    }

    rs=ixc_route_init();
    if(rs<0){
        STDERR("cannot init route\r\n");
        return NULL;
    }

    rs=ixc_p2p_init();
    if(rs<0){
        STDERR("cannot init P2P\r\n");
        return NULL;
    }

    rs=ixc_dhcp_client_init();
    if(rs<0){
        STDERR("cannot init DHCP\r\n");
        return NULL;
    }


    return (PyObject *)self;
}

static int
router_init(routerObject *self,PyObject *args,PyObject *kwds)
{
    PyObject *fn_sent,*fn_w;

    if(!PyArg_ParseTuple(args,"OO",&fn_sent,&fn_w)) return -1;
    if(!PyCallable_Check(fn_sent)){
        PyErr_SetString(PyExc_TypeError,"packet recevice  must be callable");
        return -1;
    }
    if(!PyCallable_Check(fn_w)){
        PyErr_SetString(PyExc_TypeError,"write event set  must be callable");
        return -1;
    }

    Py_XDECREF(router_sent_cb);
    Py_XDECREF(router_write_ev_tell_cb);

    router_sent_cb=fn_sent;
    router_write_ev_tell_cb=fn_w;

    Py_INCREF(router_sent_cb);
    Py_INCREF(router_write_ev_tell_cb);

    return 0;
}

/// 发送网络数据包
static PyObject *
router_send_netpkt(PyObject *self,PyObject *args)
{
    char *sent_data;
    Py_ssize_t size;
    int flags;

    if(!PyArg_ParseTuple(args,"y#i",&sent_data,&size,&flags)) return NULL;
    if(IXC_PKT_FLAGS_IP!=flags && IXC_PKT_FLAGS_LINK!=flags){
        PyErr_SetString(PyExc_ValueError,"wrong flags value");
        return NULL;
    }

    if(IXC_PKT_FLAGS_LINK==flags){

    }else{

    }

    Py_RETURN_NONE;
}

/// 是否需要等待,如果有需要待发送的数据包等内容,那么就不能等待
static PyObject *
router_iowait(PyObject *self,PyObject *args)
{
    if(ixc_qos_have_data()){
        Py_RETURN_FALSE;
    }
    
    Py_RETURN_TRUE;
}

static PyObject *
router_myloop(PyObject *self,PyObject *args)
{
    ixc_addr_map_do();
    sysloop_do();
    
    Py_RETURN_NONE;
}

static PyObject *
router_netif_create(PyObject *self,PyObject *args)
{
    const char *name;
    char res_devname[512];
    int fd,if_idx;

    if(!PyArg_ParseTuple(args,"si",&name,&if_idx)) return NULL;
    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }
    if(ixc_netif_is_used(if_idx)){
        PyErr_SetString(PyExc_SystemError,"netif is used\r\n");
        return NULL;  
    }

    fd=ixc_netif_create(name,res_devname,if_idx);

    return Py_BuildValue("is",fd,res_devname);
}

static PyObject *
router_netif_delete(PyObject *self,PyObject *args)
{
    int if_idx;
    if(!PyArg_ParseTuple(args,"i",&if_idx)) return NULL;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }

    ixc_netif_delete(if_idx);

    Py_RETURN_NONE;
}

/// 接收数据
static PyObject *
router_netif_rx_data(PyObject *self,PyObject *args)
{
    int if_idx,rs;
    struct ixc_netif *netif;
    if(!PyArg_ParseTuple(args,"i",&if_idx)) return NULL;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }

    if(!ixc_netif_is_used(if_idx)){
        PyErr_SetString(PyExc_SystemError,"netif is not used\r\n");
        return NULL;  
    }

    netif=ixc_netif_get(if_idx);
    rs=ixc_netif_rx_data(netif);

    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

/// 发送数据
static PyObject *
router_netif_tx_data(PyObject *self,PyObject *args)
{
    int if_idx,rs;
    struct ixc_netif *netif;
    if(!PyArg_ParseTuple(args,"i",&if_idx)) return NULL;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }

    if(!ixc_netif_is_used(if_idx)){
        PyErr_SetString(PyExc_SystemError,"netif is not used\r\n");
        return NULL;  
    }

    netif=ixc_netif_get(if_idx);
    rs=ixc_netif_tx_data(netif);

    if(rs<0){
        Py_RETURN_FALSE;
    }
    
    Py_RETURN_TRUE;
}

/// 设置网卡IP地址
static PyObject *
router_netif_set_ip(PyObject *self,PyObject *args)
{
    unsigned char *ip;
    Py_ssize_t size;
    unsigned char prefix;
    int is_ipv6,if_idx;

    if(!PyArg_ParseTuple(args,"iy#bp",&if_idx,&ip,&size,&prefix,&is_ipv6)) return NULL;
    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }

    if(!ixc_netif_is_used(if_idx)){
        PyErr_SetString(PyExc_SystemError,"netif is not used");
        return NULL;  
    }
    
    if(ixc_netif_set_ip(if_idx,ip,prefix,is_ipv6)){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_netif_set_hwaddr(PyObject *self,PyObject *args)
{
    int if_idx;
    unsigned char *s;
    Py_ssize_t size;
    if(!PyArg_ParseTuple(args,"iy#",&if_idx,&s,&size)) return NULL;
    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }
    if(!ixc_netif_is_used(if_idx)){
        PyErr_SetString(PyExc_SystemError,"netif is not used");
        return NULL;  
    }

    if(6!=size){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr length");
        return NULL;  
    }

    ixc_netif_set_hwaddr(if_idx,s);

    Py_RETURN_NONE;
}

static PyObject *
router_dhcp_client_enable(PyObject *self,PyObject *args)
{
    int enable;
    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;

    ixc_dhcp_client_enable(enable);

    Py_RETURN_NONE;
}

static PyMemberDef router_members[]={
    {NULL}
};

static PyMethodDef routerMethods[]={
    {"send_netpkt",(PyCFunction)router_send_netpkt,METH_VARARGS,"send network packet to protocol statck"},
    {"iowait",(PyCFunction)router_iowait,METH_VARARGS,"tell if wait"},
    {"myloop",(PyCFunction)router_myloop,METH_VARARGS,"loop call"},
    {"netif_create",(PyCFunction)router_netif_create,METH_VARARGS,"create tap device"},
    {"netif_delete",(PyCFunction)router_netif_delete,METH_VARARGS,"delete tap device"},
    {"netif_rx_data",(PyCFunction)router_netif_rx_data,METH_VARARGS,"receive netif data"},
    {"netif_tx_data",(PyCFunction)router_netif_tx_data,METH_VARARGS,"send netif data"},
    {"netif_set_ip",(PyCFunction)router_netif_set_ip,METH_VARARGS,"set netif ip"},
    {"netif_set_hwaddr",(PyCFunction)router_netif_set_hwaddr,METH_VARARGS,"set hardware address"},
    {"dhcp_client_enable",(PyCFunction)router_dhcp_client_enable,METH_VARARGS,"enable or disable dhcp client"},
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

    PyModule_AddIntMacro(m,IXC_PKT_FLAGS_LINK);
    PyModule_AddIntMacro(m,IXC_PKT_FLAGS_IP);

    PyModule_AddIntMacro(m,IXC_NETIF_LAN);
    //
    PyModule_AddIntMacro(m,IXC_NETIF_WAN);

    return m;
}