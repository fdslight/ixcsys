#define  PY_SSIZE_T_CLEAN
#define  PY_SSIZE_T_CLEAN

#include<Python.h>
#include<structmember.h>
#include<execinfo.h>
#include<signal.h>

#include "../src/mbuf.h"
#include "../src/debug.h"
#include "../src/ip.h"
#include "../src/ipv6.h"
#include "../src/proxy_helper.h"
#include "../src/udp.h"
#include "../src/tcp.h"
#include "../src/tcp_timer.h"
#include "../src/ipunfrag.h"
#include "../src/ip6unfrag.h"

#include "../../../pywind/clib/sysloop.h"

typedef struct{
    PyObject_HEAD
}proxy_helper_object;

/// TCP发送回调函数
static PyObject *ip_sent_cb=NULL;
/// TCP连接事件回调函数
static PyObject *tcp_conn_ev_cb=NULL;
/// TCP关闭事件回调函数
static PyObject *tcp_close_ev_cb=NULL;
/// TCP接收回调函数
static PyObject *tcp_recv_cb=NULL;
/// UDP接收回调函数
static PyObject *udp_recv_cb=NULL;

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

int netpkt_send(struct mbuf *m,unsigned char protocol,int is_ipv6)
{
    PyObject *arglist,*result;

    if(NULL==ip_sent_cb){
        STDERR("not set ip_sent_cb\r\n");
        return -1;
    }

    arglist=Py_BuildValue("(iy#)",protocol,m->data+m->begin,m->end-m->begin);
    result=PyObject_CallObject(ip_sent_cb,arglist);
 
    Py_XDECREF(arglist);
    Py_XDECREF(result);

    mbuf_put(m);

    return 0;
}


int netpkt_tcp_connect_ev(unsigned char *id,unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_ipv6)
{
    PyObject *arglist,*result;
    Py_ssize_t size=is_ipv6?36:12;
    char src_addr[512],dst_addr[512];

    if(NULL==tcp_conn_ev_cb){
        STDERR("not set tcp_conn_ev_cb\r\n");
        return -1;
    }

    bzero(src_addr,512);
    bzero(dst_addr,512);

    if(is_ipv6){
        inet_ntop(AF_INET6,saddr,src_addr,512);
        inet_ntop(AF_INET6,daddr,dst_addr,512);
    }else{
        inet_ntop(AF_INET,saddr,src_addr,512);
        inet_ntop(AF_INET,daddr,dst_addr,512);
    }

    arglist=Py_BuildValue("(y#ssHHN)",id,size,src_addr,dst_addr,sport,dport,PyBool_FromLong(is_ipv6));
    result=PyObject_CallObject(tcp_conn_ev_cb,arglist);
 
    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0;
}

int netpkt_tcp_recv(unsigned char *id,unsigned short win_size,int is_ipv6,void *data,int length)
{
    PyObject *arglist,*result;
    Py_ssize_t size=is_ipv6?36:12;

    if(NULL==tcp_recv_cb){
        STDERR("not set tcp_recv_cb\r\n");
        return -1;
    }

    arglist=Py_BuildValue("(y#HNy#)",id,size,win_size,PyBool_FromLong(is_ipv6),data,length);
    result=PyObject_CallObject(tcp_recv_cb,arglist);
 
    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0;
}

int netpkt_tcp_close_ev(unsigned char *id,int is_ipv6)
{
    PyObject *arglist,*result;
    Py_ssize_t size=is_ipv6?36:12;

    if(NULL==tcp_close_ev_cb){
        STDERR("not set tcp_close_ev_cb\r\n");
        return -1;
    }
    
    arglist=Py_BuildValue("(y#N)",id,size,PyBool_FromLong(is_ipv6));
    result=PyObject_CallObject(tcp_close_ev_cb,arglist);
 
    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0;
}

int netpkt_udp_recv(unsigned char *saddr,unsigned char *daddr,unsigned short sport,unsigned short dport,int is_udplite,int is_ipv6,void *data,int size)
{
    PyObject *arglist,*result;
    char src_addr[512],dst_addr[512];
    int fa;

    if(NULL==udp_recv_cb){
        STDERR("not set udp_recv_cb\r\n");
        return -1;
    }

    fa=is_ipv6?AF_INET6:AF_INET;

    bzero(src_addr,512);
    bzero(dst_addr,512);

    inet_ntop(fa,saddr,src_addr,512);
    inet_ntop(fa,daddr,dst_addr,512);

    arglist=Py_BuildValue("(ssHHNNy#)",src_addr,dst_addr,sport,dport,PyBool_FromLong(is_udplite),PyBool_FromLong(is_ipv6),data,size);
    result=PyObject_CallObject(udp_recv_cb,arglist);
 
    Py_XDECREF(arglist);
    Py_XDECREF(result);

    return 0; 
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

    rs=ipunfrag_init();
    if(rs<0){
        STDERR("cannot init ipunfrag\r\n");
        return NULL;
    }

    rs=ip6unfrag_init();
    if(rs<0){
        STDERR("cannot init ip6unfrag\r\n");
        return NULL;
    }
    
    // tcp timer需要在tcp之前初始化
    rs=tcp_timer_init(TCP_TIMEOUT_MAX,TCP_TIMER_TICK_INTERVAL);
    if(rs<0){
        STDERR("cannot init tcp timer\r\n");
        return NULL;
    }

    rs=tcp_init();
    if(rs<0){
        STDERR("cannot init tcp\r\n");
        return NULL;
    }

    signal(SIGSEGV,ixc_segfault_handle);

    return (PyObject *)self;
}

static int
proxy_helper_init(proxy_helper_object *self,PyObject *args,PyObject *kwds)
{
    PyObject *fn_ip_sent_cb;
    PyObject *fn_tcp_conn_ev_cb,*fn_tcp_close_ev_cb,*fn_tcp_recv_cb;
    PyObject *fn_udp_recv_cb;

    if(!PyArg_ParseTuple(args,"OOOOO",&fn_ip_sent_cb,&fn_tcp_conn_ev_cb,&fn_tcp_recv_cb,&fn_tcp_close_ev_cb,&fn_udp_recv_cb)) return -1;
    if(!PyCallable_Check(fn_ip_sent_cb)){
        PyErr_SetString(PyExc_TypeError,"ip sent callback function  must be callable");
        return -1;
    }
    if(!PyCallable_Check(fn_tcp_conn_ev_cb)){
        PyErr_SetString(PyExc_TypeError,"tcp conn event callback function  must be callable");
        return -1;
    }
    if(!PyCallable_Check(fn_tcp_recv_cb)){
        PyErr_SetString(PyExc_TypeError,"tcp recv callback function  must be callable");
        return -1;
    }
    if(!PyCallable_Check(fn_tcp_close_ev_cb)){
        PyErr_SetString(PyExc_TypeError,"tcp close event callback function  must be callable");
        return -1;
    }

    if(!PyCallable_Check(fn_udp_recv_cb)){
        PyErr_SetString(PyExc_TypeError,"udp recv callback function  must be callable");
        return -1;
    }

    Py_XDECREF(ip_sent_cb);

    Py_XDECREF(tcp_conn_ev_cb);
    Py_XDECREF(tcp_recv_cb);
    Py_XDECREF(tcp_close_ev_cb);

    Py_XDECREF(udp_recv_cb);

    ip_sent_cb=fn_ip_sent_cb;

    tcp_conn_ev_cb=fn_tcp_conn_ev_cb;
    tcp_recv_cb=fn_tcp_recv_cb;
    tcp_close_ev_cb=fn_tcp_close_ev_cb;

    udp_recv_cb=fn_udp_recv_cb;

    Py_INCREF(ip_sent_cb);

    Py_INCREF(tcp_conn_ev_cb);
    Py_INCREF(tcp_recv_cb);
    Py_INCREF(tcp_close_ev_cb);

    Py_INCREF(udp_recv_cb);   

    return 0;
}

static PyObject *
proxy_helper_myloop(PyObject *self,PyObject *args)
{
    sysloop_do();
    Py_RETURN_NONE;
}

static PyObject *
proxy_helper_mtu_set(PyObject *self,PyObject *args)
{
    int mtu,is_ipv6;
    if(!PyArg_ParseTuple(args,"ip",&mtu,&is_ipv6)) return NULL;

    if(mtu<576 || mtu > 9000){
        PyErr_SetString(PyExc_ValueError,"mtu must be 576 to 9000");
        return NULL;
    }

    if(is_ipv6) ipv6_mtu_set(mtu);
    else ip_mtu_set(mtu);

    Py_RETURN_NONE;
}

/// 处理接收到的网络数据包
static PyObject *
proxy_helper_netpkt_handle(PyObject *self,PyObject *args)
{
    const char *s;
    Py_ssize_t size;
    struct mbuf *m;

    if(!PyArg_ParseTuple(args,"y#",&s,&size)) return NULL;
    if(size<28){
        STDERR("wrong IP data format\r\n");
        Py_RETURN_FALSE;
    }

    m=mbuf_get();
    if(NULL==m){
        STDERR("cannot get mbuf\r\n");
        Py_RETURN_FALSE;
    }

    m->begin=m->offset=MBUF_BEGIN;
    m->end=m->tail=m->begin+size;

    memcpy(m->data+m->offset,s,size);
    ip_handle(m);

    Py_RETURN_TRUE;
}

/// 发送UDP数据包
static PyObject *
proxy_helper_udp_send(PyObject *self,PyObject *args)
{
    unsigned char *saddr,*daddr;
    char *data;
    Py_ssize_t saddr_s,daddr_s,data_s;
    unsigned short sport,dport,csum_coverage;
    int is_ipv6,is_udplite;

    if(!PyArg_ParseTuple(args,"y#y#HHppHy#",&saddr,&saddr_s,&daddr,&daddr_s,&sport,&dport,&is_udplite,&is_ipv6,&csum_coverage,&data,&data_s)) return NULL;

    if(is_ipv6 && (saddr_s!=16 || daddr_s!=16)){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 source address or destination address value");
        return NULL;
    }

    if(!is_ipv6 && (saddr_s!=4 || daddr_s!=4)){
        PyErr_SetString(PyExc_ValueError,"wrong IP source address or destination address value");
        return NULL;
    }

    udp_send(saddr,daddr,sport,dport,is_udplite,is_ipv6,csum_coverage,data,data_s);
    Py_RETURN_NONE;
}

/// 发送TCP数据包
static PyObject *
proxy_helper_tcp_send(PyObject *self,PyObject *args)
{
    int is_ipv6,r;
    unsigned char *session_id;
    unsigned char *data;
    Py_ssize_t id_s,data_s;

    if(!PyArg_ParseTuple(args,"y#y#p",&session_id,&id_s,&data,&data_s,&is_ipv6)) return NULL;

    if(is_ipv6 && id_s!=36){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 TCP session ID");
        return NULL;
    }

    if(!is_ipv6 && id_s!=12){
        PyErr_SetString(PyExc_ValueError,"wrong IP TCP session ID");
        return NULL;
    }

    r=tcp_send(session_id,data,data_s,is_ipv6);

    return PyLong_FromLong(r);
}

/// 设置TCP的窗口大小
static PyObject *
proxy_helper_tcp_win_set(PyObject *self,PyObject *args)
{
    int is_ipv6;
    unsigned char *session_id;
    unsigned short win_size;
    Py_ssize_t id_s;

    if(!PyArg_ParseTuple(args,"y#pH",&session_id,&id_s,&is_ipv6,&win_size)) return NULL;
    if(is_ipv6 && id_s!=36){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 TCP session ID");
        return NULL;
    }
    if(!is_ipv6 && id_s!=12){
        PyErr_SetString(PyExc_ValueError,"wrong IP TCP session ID");
        return NULL;
    }
    tcp_window_set(session_id,is_ipv6,win_size);
    
    Py_RETURN_NONE;
}

/// TCP连接关闭
static PyObject *
proxy_helper_tcp_close(PyObject *self,PyObject *args)
{
    int is_ipv6,rs;
    unsigned char *session_id;
    Py_ssize_t id_s;

    if(!PyArg_ParseTuple(args,"y#p",&session_id,&id_s,&is_ipv6)) return NULL;

    if(is_ipv6 && id_s!=36){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 TCP session ID");
        return NULL;
    }

    if(!is_ipv6 && id_s!=12){
        PyErr_SetString(PyExc_ValueError,"wrong IP TCP session ID");
        return NULL;
    }

    // 此处关闭TCP连接
    rs=tcp_close(session_id,is_ipv6);

    if(rs!=0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

/// 设置MSS值
static PyObject *
proxy_helper_tcp_mss_set(PyObject *self,PyObject *args)
{
    unsigned short mss;
    int is_ipv6,r;

    if(!PyArg_ParseTuple(args,"Hp",&mss,&is_ipv6)) return NULL;

    r=tcp_mss_set(mss,is_ipv6);
    if(!r){
        Py_RETURN_TRUE;
    }

    Py_RETURN_FALSE;
}

/// 检查是否还有数据
static PyObject *
proxy_helper_io_wait(PyObject *self,PyObject *args)
{
    unsigned long long conns=tcp_conn_count_get();

    if(conns){
        Py_RETURN_FALSE;
    }
    
    Py_RETURN_TRUE;
}

static PyMemberDef proxy_helper_members[]={
    {NULL}
};

static PyMethodDef proxy_helper_methods[]={
    {"myloop",(PyCFunction)proxy_helper_myloop,METH_VARARGS,"loop call"},
    {"mtu_set",(PyCFunction)proxy_helper_mtu_set,METH_VARARGS,"set mtu for IP and IPv6"},

    {"netpkt_handle",(PyCFunction)proxy_helper_netpkt_handle,METH_VARARGS,"handle ip data packet"},

    {"udp_send",(PyCFunction)proxy_helper_udp_send,METH_VARARGS,"udp data send"},

    {"tcp_send",(PyCFunction)proxy_helper_tcp_send,METH_VARARGS,"tcp data send"},
    {"tcp_win_size_set",(PyCFunction)proxy_helper_tcp_win_set,METH_VARARGS,"tcp window size set"},
    {"tcp_close",(PyCFunction)proxy_helper_tcp_close,METH_VARARGS,"tcp connection close"},
    {"tcp_mss_set",(PyCFunction)proxy_helper_tcp_mss_set,METH_VARARGS,"tcp mss set"},

    {"io_wait",(PyCFunction)proxy_helper_io_wait,METH_VARARGS,"if wait connection IO"},
    
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
    const char *const_names[] = {
	};

	const int const_values[] = {
	};
    
    int const_count = sizeof(const_names) / sizeof(NULL);

    if(PyType_Ready(&proxy_helper_type) < 0) return NULL;

    m=PyModule_Create(&proxy_helper_module);
    if(NULL==m) return NULL;

    for (int n = 0; n < const_count; n++) {
		if (PyModule_AddIntConstant(m, const_names[n], const_values[n]) < 0) return NULL;
	}

    Py_INCREF(&proxy_helper_type);
    if(PyModule_AddObject(m,"proxy_helper",(PyObject *)&proxy_helper_type)<0){
        Py_DECREF(&proxy_helper_type);
        Py_DECREF(m);
        return NULL;
    }
    
    return m;
}