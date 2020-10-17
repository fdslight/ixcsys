#define  PY_SSIZE_T_CLEAN

#include<Python.h>
#include<structmember.h>
#include<execinfo.h>
#include<signal.h>

#include "../src/mbuf.h"
#include "../src/router.h"
#include "../src/netif.h"
#include "../src/addr_map.h"
#include "../src/qos.h"
#include "../src/route.h"
#include "../src/udp_src_filter.h"
#include "../src/vpn.h"
#include "../src/ether.h"
#include "../src/ip.h"
#include "../src/ip6.h"
#include "../src/local.h"
#include "../src/nat.h"
#include "../src/natv6.h"
#include "../src/pppoe.h"
#include "../src/debug.h"

#include "../../../pywind/clib/sysloop.h"
#include "../../../pywind/clib/netif/tuntap.h"

typedef struct{
    PyObject_HEAD
}routerObject;

static PyObject *router_sent_cb=NULL;
static PyObject *router_write_ev_tell_cb=NULL;
static PyObject *router_pppoe_session_packet_recv_cb=NULL;

int ixc_router_send(unsigned char if_type,unsigned char ipproto,unsigned char flags,void *buf,size_t size)
{
    PyObject *arglist,*result;
    if(NULL==router_sent_cb) return -1;

    arglist=Py_BuildValue("(bbby#)",if_type,ipproto,flags,buf,size);
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

int ixc_router_pppoe_session_send(unsigned short protocol,unsigned short length,void *data)
{
    PyObject *arglist,*result;
    unsigned char *md5;
    Py_ssize_t size;

    if(NULL==router_pppoe_session_packet_recv_cb){
        STDERR("no set python pppoe session recv function\r\n");
        return -1;
    }

    arglist=Py_BuildValue("(Hy#)",protocol,data,length);
    result=PyObject_CallObject(router_sent_cb,arglist);

    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0;
}

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

    rs=ixc_nat_init();
    if(rs<0){
        STDERR("cannot init nat\r\n");
        return NULL;
    }

    rs=ixc_natv6_init();
    if(rs<0){
        STDERR("cannot init natv6\r\n");
        return NULL;
    }

    rs=ixc_netif_init();
    if(rs<0){
        STDERR("cannot init netif\r\n");
        return NULL;
    }

    rs=ixc_local_init();
    if(rs<0){
        STDERR("cannot init local\r\n");
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

    rs=ixc_vpn_init();
    if(rs<0){
        STDERR("cannot init vpn\r\n");
        return NULL;
    }

    rs=ixc_udp_src_filter_init();
    if(rs<0){
        STDERR("cannot init P2P\r\n");
        return NULL;
    }

    rs=ixc_pppoe_init();
    if(rs<0){
        STDERR("cannot init pppoe\r\n");
        return NULL;
    }

    signal(SIGSEGV,ixc_segfault_handle);

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

/// 重置PPPoE
static PyObject *
router_pppoe_reset(PyObject *self,PyObject *args)
{
    ixc_pppoe_reset();
    Py_RETURN_NONE;
}

/// 发送PPPoE数据
static PyObject *
router_pppoe_data_send(PyObject *self,PyObject *args)
{
    unsigned short protocol;
    unsigned char *data;

    Py_ssize_t size;

    if(!PyArg_ParseTuple(args,"Hy#",&protocol,&data,&size)) return NULL;
    ixc_pppoe_send_session_packet(protocol,size,data);

    Py_RETURN_NONE;
}

/// 设置MD5计算函数
static PyObject *
router_set_pppoe_session_packet_recv_fn(PyObject *self,PyObject *args)
{
    if(!PyArg_ParseTuple(args,"O",&router_pppoe_session_packet_recv_cb)) return NULL;
    if(PyCallable_Check(router_pppoe_session_packet_recv_cb)){
        PyErr_SetString(PyExc_TypeError,"the argument must be callable");
        return NULL;
    }

    Py_XDECREF(router_pppoe_session_packet_recv_cb);
    Py_INCREF(router_pppoe_session_packet_recv_cb);

    Py_RETURN_NONE;
}

/// 发送网络数据包
static PyObject *
router_send_netpkt(PyObject *self,PyObject *args)
{
    char *sent_data;
    Py_ssize_t size;
    unsigned char flags;
    unsigned char if_type;
    unsigned char ipproto;

    struct ixc_mbuf *m;
    struct ixc_netif *netif=NULL;

    if(!PyArg_ParseTuple(args,"bbby#",&if_type,&ipproto,&flags,&sent_data,&size)) return NULL;

    if(0==ipproto){
        netif=ixc_netif_get(if_type);
        if(NULL==netif){
            Py_RETURN_FALSE;
        }
    }

    m=ixc_mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf for send\r\n");
        Py_RETURN_FALSE;
    }

    m->netif=netif;
    m->from=IXC_MBUF_FROM_LAN;
    m->begin=IXC_MBUF_BEGIN;
    m->offset=m->begin;
    m->tail=m->begin+size;
    m->end=m->tail;

    memcpy(m->data+m->begin,sent_data,size);

    if(0!=ipproto){
        ixc_ip_send(m);
    }else{
        ixc_ether_send2(m);
    }

    Py_RETURN_TRUE;
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
    sysloop_do();
    Py_RETURN_NONE;
}

static PyObject *
router_tundev_create(PyObject *self,PyObject *args)
{
    const char *name;
    char name_new[512];
    int rs;

    if(!PyArg_ParseTuple(args,"s",&name)) return NULL;
    strcpy(name_new,name);

    rs=ixc_local_dev_create(name_new);
    if(rs<0){
        Py_RETURN_NONE;
    }

    return Py_BuildValue("is",rs,name_new);
}

static PyObject *
router_tundev_delete(PyObject *self,PyObject *args)
{
    ixc_local_dev_delete();
    
    Py_RETURN_NONE;
}

static PyObject *
router_tundev_rx_data(PyObject *self,PyObject *args)
{
    int rs=ixc_local_rx_data();

    if(rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_tundev_tx_data(PyObject *self,PyObject *args)
{
    int rs=ixc_local_tx_data();

    if(rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_tundev_set_ip(PyObject *self,PyObject *args)
{
    Py_ssize_t size;
    unsigned char *ipaddr;
    int is_ipv6,is_ipv6_local_linked;
    int rs;

    if(!PyArg_ParseTuple(args,"y#pp",&ipaddr,&size,&is_ipv6,&is_ipv6_local_linked)) return NULL;

    if(is_ipv6 && size!=16){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 address");
        return NULL;
    }

    if(!is_ipv6 && size!=4){
        PyErr_SetString(PyExc_ValueError,"wrong IP address");
        return NULL;
    }

    rs=ixc_local_set_ip(ipaddr,is_ipv6,is_ipv6_local_linked);

    return PyLong_FromLong(rs);
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

    if(if_idx<0 || if_idx>=IXC_NETIF_MAX){
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

    ixc_netif_set_hwaddr(if_idx,s);

    Py_RETURN_NONE;
}

static PyObject *
router_udp_src_filter_set_ip(PyObject *self,PyObject *args)
{
    unsigned char *subnet;
    Py_ssize_t size;
    unsigned char prefix;
    int is_ipv6,rs;

    if(!PyArg_ParseTuple(args,"y#bp",&subnet,&size,&prefix,&is_ipv6)) return NULL;

    if(is_ipv6 && prefix>128){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 prefix value");
        return NULL;  
    }

    if(!is_ipv6 && prefix>32){
        PyErr_SetString(PyExc_ValueError,"wrong IP prefix value");
        return NULL;  
    }

    rs=ixc_udp_src_filter_set_ip(subnet,prefix,is_ipv6);

    if(!rs){
        Py_RETURN_TRUE;
    }

    Py_RETURN_FALSE;
}

static PyObject *
router_udp_src_filter_enable(PyObject *self,PyObject *args)
{
    int enable,is_linked;

    if(!PyArg_ParseTuple(args,"pp",&enable,&is_linked)) return NULL;
    
    ixc_udp_src_filter_enable(enable,is_linked);

    Py_RETURN_NONE;
}

/// 添加路由
static PyObject *
router_route_add(PyObject *self,PyObject *args)
{
    unsigned char *subnet,*gw;
    Py_ssize_t size_a,size_b;
    int is_ipv6,rs,is_linked;
    unsigned char prefix;

    if(!PyArg_ParseTuple(args,"y#by#pp",&subnet,&size_a,&prefix,&gw,&size_b,&is_ipv6,&is_linked)) return NULL;

    if(is_ipv6 && prefix>128){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 prefix value");
        return NULL;  
    }

    if(!is_ipv6 && prefix>32){
        PyErr_SetString(PyExc_ValueError,"wrong IP prefix value");
        return NULL;  
    }

    if(is_ipv6 && (size_a!=16 || size_b!=16)){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 address or gateway length");
        return NULL;  
    }

    if(!is_ipv6 && (size_a!=4 || size_b!=4)){
        PyErr_SetString(PyExc_ValueError,"wrong IP address or gateway length");
        return NULL;  
    }

    rs=ixc_route_add(subnet,prefix,gw,is_ipv6,is_linked);

    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_route_del(PyObject *self,PyObject *args)
{
    unsigned char *subnet;
    unsigned char prefix;
    Py_ssize_t size;
    int is_ipv6;

    if(!PyArg_ParseTuple(args,"y#bp",&subnet,&size,&prefix,&is_ipv6)) return NULL;

    if(is_ipv6 && prefix>128){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 prefix value");
        return NULL;  
    }

    if(!is_ipv6 && prefix>32){
        PyErr_SetString(PyExc_ValueError,"wrong IP prefix value");
        return NULL;  
    }

    if(is_ipv6 && size!=16){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 address or gateway length");
        return NULL;  
    }

    if(!is_ipv6 && size!=4){
        PyErr_SetString(PyExc_ValueError,"wrong IP address or gateway length");
        return NULL;  
    }

    ixc_route_del(subnet,prefix,is_ipv6);

    Py_RETURN_NONE;
}

static PyObject *
router_nat_set(PyObject *self,PyObject *args)
{
    int status,type,is_ipv6;
    int rs;

    if(!PyArg_ParseTuple(args,"pip",&status,&type,&is_ipv6)) return NULL;

    if(is_ipv6) rs=ixc_natv6_enable(status,type);
    else rs=ixc_nat_enable(status,type);

    if(rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_pppoe_enable(PyObject *self,PyObject *args)
{
    int status;
    if(!PyArg_ParseTuple(args,"p",&status)) return NULL;
    ixc_pppoe_enable(status);

    Py_RETURN_NONE;
}

static PyObject *
router_pppoe_is_enabled(PyObject *self,PyObject *args)
{
    if(ixc_pppoe_is_enabled()){
        Py_RETURN_TRUE;
    }

    Py_RETURN_FALSE;
}

static PyObject *
router_pppoe_start(PyObject *self,PyObject *args)
{
    ixc_pppoe_start();
    Py_RETURN_NONE;
}

static PyObject *
router_pppoe_stop(PyObject *self,PyObject *args)
{
    ixc_pppoe_stop();
    Py_RETURN_NONE;
}

static PyObject *
router_pppoe_ok(PyObject *self,PyObject *args)
{
    if(ixc_pppoe_ok()){
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static PyObject *
router_pppoe_set_user(PyObject *self,PyObject *args)
{
    const char *user,*passwd;
    int rs;

    if(!PyArg_ParseTuple(args,"ss",&user,&passwd)) return NULL;

    rs=ixc_pppoe_set_user(user,passwd);
    if(rs){
        Py_RETURN_FALSE;
    }
    Py_RETURN_TRUE;
}


static PyMemberDef router_members[]={
    {NULL}
};

static PyMethodDef routerMethods[]={
    {"set_pppoe_session_packet_recv_fn",(PyCFunction)router_set_pppoe_session_packet_recv_fn,METH_VARARGS,"set PPPoE session packet recv function"},
    {"send_netpkt",(PyCFunction)router_send_netpkt,METH_VARARGS,"send network packet to protocol statck"},
    //
    {"iowait",(PyCFunction)router_iowait,METH_VARARGS,"tell if wait"},
    //
    {"myloop",(PyCFunction)router_myloop,METH_VARARGS,"loop call"},
    //
    {"tundev_create",(PyCFunction)router_tundev_create,METH_VARARGS,"create tun device"},
    {"tundev_delete",(PyCFunction)router_tundev_delete,METH_NOARGS,"delete tun device"},
    {"tundev_rx_data",(PyCFunction)router_tundev_rx_data,METH_NOARGS,"read tun device data"},
    {"tundev_tx_data",(PyCFunction)router_tundev_tx_data,METH_NOARGS,"tun device data write"},
    {"tundev_set_ip",(PyCFunction)router_tundev_set_ip,METH_VARARGS,"set local ip address"},
    //
    {"netif_create",(PyCFunction)router_netif_create,METH_VARARGS,"create tap device"},
    {"netif_delete",(PyCFunction)router_netif_delete,METH_VARARGS,"delete tap device"},
    {"netif_rx_data",(PyCFunction)router_netif_rx_data,METH_VARARGS,"receive netif data"},
    {"netif_tx_data",(PyCFunction)router_netif_tx_data,METH_VARARGS,"send netif data"},
    {"netif_set_ip",(PyCFunction)router_netif_set_ip,METH_VARARGS,"set netif ip"},
    {"netif_set_hwaddr",(PyCFunction)router_netif_set_hwaddr,METH_VARARGS,"set hardware address"},
    //
    {"udp_src_filter_set_ip",(PyCFunction)router_udp_src_filter_set_ip,METH_VARARGS,"set udp source filter IP address range"},
    {"udp_src_filter_enable",(PyCFunction)router_udp_src_filter_enable,METH_VARARGS,"enable/disable udp source filter"},
    //
    {"route_add",(PyCFunction)router_route_add,METH_VARARGS,"add route"},
    {"route_del",(PyCFunction)router_route_del,METH_VARARGS,"delete route"},
    //
    {"nat_set",(PyCFunction)router_nat_set,METH_VARARGS,"set IP NAT and IPv6 NAT status and type"},
    //
    {"pppoe_enable",(PyCFunction)router_pppoe_enable,METH_VARARGS,"enable or disable pppoe"},
    {"pppoe_is_enabled",(PyCFunction)router_pppoe_is_enabled,METH_NOARGS,"check pppoe is enabled"},
    {"pppoe_start",(PyCFunction)router_pppoe_start,METH_NOARGS,"start pppoe"},
    {"pppoe_stop",(PyCFunction)router_pppoe_stop,METH_NOARGS,"stop pppoe"},
    {"pppoe_ok",(PyCFunction)router_pppoe_ok,METH_NOARGS,"check pppoe ok"},
    {"pppoe_set_user",(PyCFunction)router_pppoe_set_user,METH_VARARGS,"set pppoe user and password"},
    //
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

    PyModule_AddIntMacro(m,IXC_FLAG_ARP);
    PyModule_AddIntMacro(m,IXC_FLAG_DHCP_CLIENT);
    PyModule_AddIntMacro(m,IXC_FLAG_DHCP_SERVER);
    PyModule_AddIntMacro(m,IXC_FLAG_L2VPN);
    PyModule_AddIntMacro(m,IXC_FLAG_SRC_UDP_FILTER);
    PyModule_AddIntMacro(m,IXC_FLAG_ROUTE_FWD);

    PyModule_AddIntMacro(m,IXC_NETIF_LAN);
    //
    PyModule_AddIntMacro(m,IXC_NETIF_WAN);

    return m;
}