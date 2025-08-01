#include<unistd.h>
#include<signal.h>
#include<stdlib.h>
#include<execinfo.h>
#include<libgen.h>
#include<time.h>

#include<sched.h>
#include<sys/resource.h>

#define  PY_SSIZE_T_CLEAN
#include<Python.h>
#include<structmember.h>

#include "mbuf.h"
#include "router.h"
#include "netif.h"
#include "addr_map.h"
#include "qos.h"
#include "route.h"
#include "src_filter.h"
#include "ether.h"
#include "ip.h"
#include "ip6.h"
#include "nat.h"
#include "pppoe.h"
#include "ipunfrag.h"
#include "debug.h"
#include "ip6sec.h"
#include "port_map.h"
#include "global.h"
#include "npfwd.h"
#include "sec_net.h"
#include "traffic_log.h"
#include "icmpv6.h"
#include "passthrough.h"
#include "nat66.h"

#include "../../../pywind/clib/pycall.h"
#include "../../../pywind/clib/debug.h"
#include "../../../pywind/clib/ev/ev.h"
#include "../../../pywind/clib/ev/rpc.h"
#include "../../../pywind/clib/pfile.h"
#include "../../../pywind/clib/sysloop.h"

/// 进程文件路径
static char pid_path[4096];
/// 运行目录
static char run_dir[4096];
/// RPC共享路径
static char rpc_path[4096];

/// 路由器运行开始时间
static time_t run_start_time=0;

static PyObject *py_helper_module=NULL;
static PyObject *py_helper_instance=NULL;

static struct ev_set ixc_ev_set;
///循环更新事件
static time_t loop_time_up=0;

typedef struct{
    PyObject_HEAD
}routerObject;

static void
router_dealloc(routerObject *self)
{
    
}

static PyObject *
router_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    routerObject *self;
    self=(routerObject *)type->tp_alloc(type,0);
    if(NULL==self) return NULL;

    return (PyObject *)self;
}

static int
router_init(routerObject *self,PyObject *args,PyObject *kwds)
{
    return 0;
}

static PyObject *
router_mbuf_alloc_info_get_for_debug(PyObject *self,PyObject *args)
{
    size_t pre_alloc_num,used_num,cur_pool_num,max_num;

    mbuf_alloc_info_get_for_debug(&pre_alloc_num,&used_num,&cur_pool_num,&max_num);
    
    return Py_BuildValue("(nnnn)",pre_alloc_num,used_num,cur_pool_num,max_num);
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

/// 获取网卡IP地址
static PyObject *
router_netif_get_ip(PyObject *self,PyObject *args)
{
    int type,is_ipv6,prefix;
    struct ixc_netif *netif;
    char str_ip[512];

    if(!PyArg_ParseTuple(args,"ip",&type,&is_ipv6)) return NULL;

    netif=ixc_netif_get(type);
    if(NULL==netif){
        Py_RETURN_NONE;
    }

    if(is_ipv6 && !netif->isset_ip6){
        Py_RETURN_NONE;
    }

    if(!is_ipv6 && !netif->isset_ip){
        Py_RETURN_NONE;
    }

    if(is_ipv6){
        inet_ntop(AF_INET6,netif->ip6addr,str_ip,512);
        prefix=netif->ip6_prefix;
    }else{
        inet_ntop(AF_INET,netif->ipaddr,str_ip,512);
        prefix=netif->ip_prefix;
    }

    return Py_BuildValue("(si)",str_ip,prefix);
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
router_netif_mtu_set(PyObject *self,PyObject *args)
{
    int if_idx,is_ipv6,rs;
    unsigned short mtu;

    if(!PyArg_ParseTuple(args,"iHp",&if_idx,&mtu,&is_ipv6)) return NULL;

    if(if_idx<0 || if_idx>IXC_NETIF_MAX){
        PyErr_SetString(PyExc_ValueError,"wrong if index value");
        return NULL;
    }

    if(mtu>1500){
        PyErr_SetString(PyExc_ValueError,"wrong MTU value");
        return NULL;
    }

    if(is_ipv6 && mtu<1280){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 MTU value");
        return NULL;
    }

    if(!is_ipv6 && mtu<576){
        PyErr_SetString(PyExc_ValueError,"wrong IPv4 MTU value");
        return NULL;
    }

    rs=ixc_netif_mtu_set(if_idx,mtu,is_ipv6);
    if(rs!=0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_netif_wan6_iface_id_set(PyObject *self,PyObject *args)
{
    unsigned char *id;
    Py_ssize_t size;
    int rs;

    if(!PyArg_ParseTuple(args,"y#",&id,&size)) return NULL;
    if(16!=size){
        PyErr_SetString(PyExc_ValueError,"wrong interface id size,it must be 16");
        return NULL;
    }

    rs=ixc_netif_wan6_iface_id_set(id);
    if(0!=rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_netif_traffic_get(PyObject *self,PyObject *args)
{
    unsigned long long rx_traffic,tx_traffic;
    int if_type;
    PyObject *res;

    if(!PyArg_ParseTuple(args,"i",&if_type)) return NULL;

    rx_traffic=0;
    tx_traffic=0;

    ixc_netif_traffic_get(if_type,&rx_traffic,&tx_traffic);

    res=Py_BuildValue("(KK)",rx_traffic,tx_traffic);
    
    return res;
}

static PyObject *
router_netif_traffic_speed_get(PyObject *self,PyObject *args)
{
    unsigned long long rx_traffic_speed,tx_traffic_speed,rx_npkt_speed,tx_npkt_speed;
    int if_type;
    PyObject *res;

    if(!PyArg_ParseTuple(args,"i",&if_type)) return NULL;

    rx_traffic_speed=0;
    tx_traffic_speed=0;
    rx_npkt_speed=0;
    tx_npkt_speed=0;

    ixc_netif_traffic_speed_get(if_type,&rx_traffic_speed,&tx_traffic_speed,&rx_npkt_speed,&tx_npkt_speed);

    res=Py_BuildValue("(KKKK)",rx_traffic_speed,tx_traffic_speed,rx_npkt_speed,tx_npkt_speed);
    
    return res;
}

static PyObject *
router_src_filter_add_hwaddr(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    Py_ssize_t size;
    if(!PyArg_ParseTuple(args,"y#",&hwaddr,&size)) return NULL;
    if(6!=size){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr value");
        return NULL;  
    }

    if(ixc_src_filter_add_hwaddr(hwaddr)){
        Py_RETURN_TRUE;
    }else{
        Py_RETURN_FALSE;
    }
}

static PyObject *
router_src_filter_del_hwaddr(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    Py_ssize_t size;
    if(!PyArg_ParseTuple(args,"y#",&hwaddr,&size)) return NULL;  
    if(6!=size){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr value");
        return NULL;  
    }
    ixc_src_filter_del_hwaddr(hwaddr);

    Py_RETURN_NONE;
}
/*
static PyObject *
router_src_filter_set_ip(PyObject *self,PyObject *args)
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

    rs=ixc_src_filter_set_ip(subnet,prefix,is_ipv6);

    if(!rs){
        Py_RETURN_TRUE;
    }

    Py_RETURN_FALSE;
}*/

static PyObject *
router_src_filter_enable(PyObject *self,PyObject *args)
{
    int enable;

    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;
    
    ixc_src_filter_enable(enable);

    Py_RETURN_NONE;
}

static PyObject *
router_src_filter_set_protocols(PyObject *self,PyObject *args)
{
    unsigned char *protocols;
    Py_ssize_t size;

    if(!PyArg_ParseTuple(args,"y#",&protocols,&size)) return NULL;
    if(size!=0xff){
        PyErr_SetString(PyExc_ValueError,"wrong protocol format length");
        return NULL;
    }

    ixc_src_filter_set_protocols(protocols);

    Py_RETURN_NONE;
}

/// 设置路由器自身IP地址
static PyObject *
router_g_manage_addr_set(PyObject *self,PyObject *args)
{
    const char *s;
    int is_ipv6;
    unsigned char n_addr[16];

    if(!PyArg_ParseTuple(args,"sp",&s,&is_ipv6)) return NULL;

    if(is_ipv6) inet_pton(AF_INET6,s,n_addr);
    else inet_pton(AF_INET,s,n_addr);

    ixc_g_manage_addr_set(n_addr,is_ipv6);

    Py_RETURN_TRUE;
}

static PyObject *
router_ip6sec_enable(PyObject *self,PyObject *args)
{
    int enable;
    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;

    ixc_ip6sec_enable(enable);

    Py_RETURN_NONE;
}

static PyObject *
router_ip_4in6_enable(PyObject *self,PyObject *args)
{
    unsigned char *peer_ip6_address;
    Py_ssize_t size;
    int enable,rs;

    if(!PyArg_ParseTuple(args,"py#",&enable,&peer_ip6_address,&size)) return NULL;

    if(16!=size){
        PyErr_SetString(PyExc_ValueError,"wrong interface id size,it must be 16");
        return NULL;
    }

    rs=ixc_ip_enable_4in6(enable,peer_ip6_address);
    if(rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_ip6_nat66_enable(PyObject *self,PyObject *args)
{
    int enable;
    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;

    ixc_nat66_enable(enable);

    Py_RETURN_NONE;
}

/// 添加路由
static PyObject *
router_route_add(PyObject *self,PyObject *args)
{
    unsigned char *subnet,*gw;
    Py_ssize_t size_a,size_b;
    int is_ipv6,rs;
    unsigned char prefix;
    unsigned char zeros[16];

    if(!PyArg_ParseTuple(args,"y#by#p",&subnet,&size_a,&prefix,&gw,&size_b,&is_ipv6)) return NULL;

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

    bzero(zeros,16);
    if(is_ipv6){
        if(!memcmp(zeros,gw,16)) gw=NULL;
    }else{
        if(!memcmp(zeros,gw,4)) gw=NULL;
    }

    rs=ixc_route_add(subnet,prefix,gw,is_ipv6);

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
router_route_ipv6_pass_enable(PyObject *self,PyObject *args)
{
    int enable;
    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;

    ixc_route_ipv6_pass_enable(enable);

    Py_RETURN_NONE;
}

static PyObject *
router_route_tcp_mss_set(PyObject *self,PyObject *args)
{
    unsigned short tcp_mss;
    int is_ipv6,rs;
    if(!PyArg_ParseTuple(args,"Hp",&tcp_mss,&is_ipv6)) return NULL;

    rs=ixc_route_tcp_mss_set(tcp_mss,is_ipv6);

    return PyBool_FromLong(rs);
}

static PyObject *
router_dns_drop_no_system_enable(PyObject *self,PyObject *args)
{
    int status,is_ipv6;
    if(!PyArg_ParseTuple(args,"pp",&status,&is_ipv6)) return NULL;
    
    if(is_ipv6) ixc_ip6_no_system_dns_drop_enable(status);
    else ixc_ip_no_system_dns_drop_enable(status);

    Py_RETURN_NONE;
}

static PyObject *
router_icmpv6_dns_set(PyObject *self,PyObject *args)
{
    unsigned char *dnsserver;
    Py_ssize_t size;

    if(!PyArg_ParseTuple(args,"y#",&dnsserver,&size)) return NULL;

    if(size!=16){
        PyErr_SetString(PyExc_ValueError,"wrong IPv6 address or gateway length");
        return NULL;  
    }

    ixc_icmpv6_dns_set(dnsserver);

    Py_RETURN_NONE;
}

static PyObject *
router_icmpv6_dns_unset(PyObject *self,PyObject *args)
{
    ixc_icmpv6_dns_unset();

    Py_RETURN_NONE;
}

static PyObject *
router_icmpv6_wan_dnsserver_get(PyObject *self,PyObject *args)
{
    unsigned char dns_a[16],dns_b[16];
    ixc_icmpv6_wan_dnsserver_get(dns_a,dns_b);

    return Py_BuildValue("(y#y#)",dns_a,16,dns_b,16);
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
router_pppoe_set_ok(PyObject *self,PyObject *args)
{
    int ok;
    if(!PyArg_ParseTuple(args,"p",&ok)) return NULL;

    ixc_pppoe_set_ok(ok);

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

/// 重置PPPoE
static PyObject *
router_pppoe_reset(PyObject *self,PyObject *args)
{
    ixc_pppoe_reset();
    Py_RETURN_NONE;
}

/// 强制指定PPPoE AC
static PyObject *
router_pppoe_force_ac_name(PyObject *self,PyObject *args)
{
    const char *ac_name;
    int is_forced;

    if(!PyArg_ParseTuple(args,"sp",&ac_name,&is_forced)) return NULL;

    ixc_pppoe_force_ac_name(ac_name,is_forced);

    Py_RETURN_NONE;
}

static PyObject *
router_pppoe_set_service_name(PyObject *self,PyObject *args)
{
    const char *service_name;
    int rs;

    if(!PyArg_ParseTuple(args,"s",&service_name)) return NULL;
    rs=ixc_pppoe_set_service_name(service_name);
    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_pppoe_set_host_uniq(PyObject *self,PyObject *args)
{
    const char *s;
    Py_ssize_t length;
    int rs;

    if(!PyArg_ParseTuple(args,"y#",&s,&length)) return NULL;

    rs=ixc_pppoe_set_host_uniq(s,length);

    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

/// 端口映射添加
static PyObject *
router_port_map_add(PyObject *self,PyObject *args)
{
    unsigned short port;
    unsigned char protocol;
    const char *address;
    unsigned char naddr[4];
    int rs;

    if(!PyArg_ParseTuple(args,"BHs",&protocol,&port,&address)) return NULL;
    inet_pton(AF_INET,address,naddr);

    if(protocol!=6 && protocol!=17 && protocol!=136){
        STDERR("unsupported protocol %d\r\n",protocol);
        Py_RETURN_FALSE;
    }

    rs=ixc_port_map_add(naddr,protocol,port);
    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

/// 端口映射删除
static PyObject *
router_port_map_del(PyObject *self,PyObject *args)
{
    unsigned short port;
    unsigned char protocol;

    if(!PyArg_ParseTuple(args,"BH",&protocol,&port)) return NULL;

    ixc_port_map_del(protocol,port);

    Py_RETURN_TRUE;

}

/// C语言LOG设置
static PyObject *
router_clog_set(PyObject *self,PyObject *args)
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

/// 检查WAN是否准备妥当
static PyObject *
router_wan_ready_ok(PyObject *self,PyObject *args)
{
    struct ixc_netif *netif=ixc_netif_get(IXC_NETIF_WAN);
    struct ixc_netif *lan_if=ixc_netif_get(IXC_NETIF_LAN);

    if(netif->isset_ip){
        Py_RETURN_TRUE;
    }

    if(lan_if->isset_ip6){
        Py_RETURN_TRUE; 
    }

    Py_RETURN_FALSE;
}

static PyObject *
router_wan_ip6_ready_ok(PyObject *self,PyObject *args)
{
    //获取IPv6地址时程序只会设置lan口的ip地址
    struct ixc_netif *lan_if=ixc_netif_get(IXC_NETIF_LAN);

    if(lan_if->isset_ip6){
        Py_RETURN_TRUE;
    }
    
    Py_RETURN_FALSE;
}

/// 打开或者关闭网络
static PyObject *
router_network_enable(PyObject *self,PyObject *args)
{
    int enable;
    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;

    ixc_g_network_enable(enable);

    Py_RETURN_NONE;
}

/// 设置重定向
static PyObject *
router_netpkt_forward_set(PyObject *self,PyObject *args)
{
    unsigned char *key;
    unsigned char *address;
    Py_ssize_t key_size;
    Py_ssize_t addr_len;
    unsigned short port;
    int flags,rs;

    if(!PyArg_ParseTuple(args,"y#y#Hi",&key,&key_size,&address,&addr_len,&port,&flags)) return NULL;

    if(key_size!=16){
        Py_RETURN_FALSE;
    }

    if(addr_len!=4){
        Py_RETURN_FALSE;
    }

    rs=ixc_npfwd_set_forward(key,address,port,flags);
    if(rs<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_netpkt_forward_disable(PyObject *self,PyObject *args)
{
    int flags;
    if(!PyArg_ParseTuple(args,"i",&flags)) return NULL;

    ixc_npfwd_disable(flags);

    Py_RETURN_NONE;
}

static PyObject *
router_sec_net_add_src(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    Py_ssize_t size;
    int action;

    if(!PyArg_ParseTuple(args,"y#i",&hwaddr,&size,&action)) return NULL;

    if(6!=size){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr length");
        return NULL;
    }

    if(ixc_sec_net_add_src(hwaddr,action)<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_sec_net_del_src(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    Py_ssize_t size;
    if(!PyArg_ParseTuple(args,"y#",&hwaddr,&size)) return NULL;

    if(6!=size){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr length");
        return NULL;
    }

    ixc_sec_net_del_src(hwaddr);
    Py_RETURN_NONE;
}

static PyObject *
router_sec_net_add_dst(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr,*subnet,prefix;
    Py_ssize_t size1,size2;
    int is_ipv6;

    if(!PyArg_ParseTuple(args,"y#y#Bp",&hwaddr,&size1,&subnet,&size2,&prefix,&is_ipv6)) 
        return NULL;

    if(6!=size1){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr length");
        return NULL;
    }

    if(is_ipv6 && prefix>128){
        PyErr_SetString(PyExc_ValueError,"wrong subnet value length for IPv6");
        return NULL;
    }

    if(!is_ipv6 && prefix>32){
        PyErr_SetString(PyExc_ValueError,"wrong subnet value length for IPv4");
        return NULL; 
    }

    if(ixc_sec_net_add_dst(hwaddr,subnet,prefix,is_ipv6)<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_net_monitor_set(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    int enable;
    Py_ssize_t size;

    if(!PyArg_ParseTuple(args,"py#",&enable,&hwaddr,&size)) return NULL;

    if(enable && 6!=size){
        PyErr_SetString(PyExc_ValueError,"wrong hwaddr length");
        return NULL;
    }

    ixc_ether_net_monitor_set(enable,hwaddr);

    Py_RETURN_NONE;
}

static PyObject *
router_qos_set_tunnel_first(PyObject *self,PyObject *args)
{
    const char *s;
    unsigned char address[16];

    int is_ipv6,rs;

    if(!PyArg_ParseTuple(args,"sp",&s,&is_ipv6)) return NULL;

    if(is_ipv6) rs=inet_pton(AF_INET6,s,address);
    else rs=inet_pton(AF_INET,s,address);

    if(rs<0){
        PyErr_SetString(PyExc_ValueError,"invalid ip address");
        return NULL;
    }

    ixc_qos_tunnel_addr_first_set(address,is_ipv6);

    Py_RETURN_NONE;
}

static PyObject *
router_qos_unset_tunnel(PyObject *self,PyObject *args)
{
    ixc_qos_tunnel_addr_first_unset();
    Py_RETURN_NONE;
}

static PyObject *
router_qos_set_mpkt_first_size(PyObject *self,PyObject *args)
{
    int size,rs;
    if(!PyArg_ParseTuple(args,"i",&size)) return NULL;
    
    rs=ixc_qos_mpkt_first_set(size);

    if(0!=rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_qos_add_first_host_hwaddr(PyObject *self,PyObject *args){
    unsigned char *hwaddr;
    Py_ssize_t size;
    int is_err;

    if(!PyArg_ParseTuple(args,"y#",&hwaddr,&size)) return NULL;

    if(6!=size){
        STDERR("wrong hwaddr length\r\n");
        Py_RETURN_FALSE;
    }

    is_err=ixc_qos_add_first_host(hwaddr);
    if(is_err){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_qos_del_first_host_hwaddr(PyObject *self,PyObject *args){
    unsigned char *hwaddr;
    Py_ssize_t size;

    if(!PyArg_ParseTuple(args,"y#",&hwaddr,&size)) return NULL;
    if(6!=size){
        STDERR("wrong hwaddr length\r\n");
        Py_RETURN_FALSE;
    }

    ixc_qos_del_first_host(hwaddr);
    Py_RETURN_NONE;
}

static PyObject *
router_passthrough_device_add(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    Py_ssize_t size;
    int rs,is_passdev;

    if(!PyArg_ParseTuple(args,"y#p",&hwaddr,&size,&is_passdev)) return NULL;

    rs=ixc_passthrough_device_add(hwaddr,is_passdev);
    if(rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_passthrough_device_del(PyObject *self,PyObject *args)
{
    unsigned char *hwaddr;
    Py_ssize_t size;
    if(!PyArg_ParseTuple(args,"y#",&hwaddr,&size)) return NULL;

    if(6!=size){
        STDERR("wrong hwaddr length\r\n");
        Py_RETURN_NONE;
    }

    ixc_passthrough_device_del(hwaddr);

    Py_RETURN_NONE;
}

static PyObject *
router_passthrough_set_vid_for_passdev(PyObject *self,PyObject *args)
{
    unsigned short vid;
    int rs;
    if(!PyArg_ParseTuple(args,"H",&vid)) return NULL;

    rs=ixc_passthrough_set_vid_for_passdev(vid);

    if(rs){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject *
router_nat_sessions_num_get(PyObject *self,PyObject *args)
{
    return PyLong_FromUnsignedLong(ixc_nat_sessions_num_get());
}

/// 返回系统的CPU总数
static PyObject *
router_cpu_num(PyObject *self,PyObject *args)
{
    int cpus=sysconf(_SC_NPROCESSORS_ONLN);

    return PyLong_FromLong(cpus);
}


/// 绑定进程到指定CPU,避免CPU上下文切换
static PyObject *
router_bind_cpu(PyObject *self,PyObject *args)
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
router_start_time(PyObject *self,PyObject *args)
{
    return PyLong_FromUnsignedLongLong(run_start_time);
}

static PyObject *
router_traffic_log_enable(PyObject *self,PyObject *args)
{
    int enable;
    if(!PyArg_ParseTuple(args,"p",&enable)) return NULL;

    if(ixc_traffic_log_enable(enable)<0){
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyMemberDef router_members[]={
    {NULL}
};

static PyMethodDef routerMethods[]={
    {"mbuf_alloc_info_get_for_debug",(PyCFunction)router_mbuf_alloc_info_get_for_debug,METH_NOARGS,"get mbuf info"},
    {"netif_create",(PyCFunction)router_netif_create,METH_VARARGS,"create tap device"},
    {"netif_delete",(PyCFunction)router_netif_delete,METH_VARARGS,"delete tap device"},
    {"netif_get_ip",(PyCFunction)router_netif_get_ip,METH_VARARGS,"get netif ip address"},
    {"netif_set_ip",(PyCFunction)router_netif_set_ip,METH_VARARGS,"set netif ip"},
    {"netif_set_hwaddr",(PyCFunction)router_netif_set_hwaddr,METH_VARARGS,"set hardware address"},
    {"netif_wan6_iface_id_set",(PyCFunction)router_netif_wan6_iface_id_set,METH_VARARGS,"set IPv6 WAN interface ID"},
    {"netif_set_mtu",(PyCFunction)router_netif_mtu_set,METH_VARARGS,"set network card MTU value"},
    {"netif_traffic_get",(PyCFunction)router_netif_traffic_get,METH_VARARGS,"get network card traffic"},
    {"netif_traffic_speed_get",(PyCFunction)router_netif_traffic_speed_get,METH_VARARGS,"get network card traffic speed"},
    //
    {"src_filter_add_hwaddr",(PyCFunction)router_src_filter_add_hwaddr,METH_VARARGS,"add hwaddr for source filter"},
    {"src_filter_del_hwaddr",(PyCFunction)router_src_filter_del_hwaddr,METH_VARARGS,"del hwaddr for source filter"},
    //{"src_filter_set_ip",(PyCFunction)router_src_filter_set_ip,METH_VARARGS,"set udp source filter IP address range"},
    {"src_filter_enable",(PyCFunction)router_src_filter_enable,METH_VARARGS,"enable/disable udp source filter"},
    {"src_filter_set_protocols",(PyCFunction)router_src_filter_set_protocols,METH_VARARGS,"set src filter protocol"},
    //
    {"g_manage_addr_set",(PyCFunction)router_g_manage_addr_set,METH_VARARGS,"set router self address"},
    //
    {"ip6sec_enable",(PyCFunction)router_ip6sec_enable,METH_VARARGS,"enable/disable IPv6 security"},
    //
    {"ip_4in6_enable",(PyCFunction)router_ip_4in6_enable,METH_VARARGS,"enable/disable 4in6 tunnel"},
    //
    {"ip6_nat66_enable",(PyCFunction)router_ip6_nat66_enable,METH_VARARGS,"enable/disable nat66"},
    //
    {"route_add",(PyCFunction)router_route_add,METH_VARARGS,"add route"},
    {"route_del",(PyCFunction)router_route_del,METH_VARARGS,"delete route"},
    {"route_ipv6_pass_enable",(PyCFunction)router_route_ipv6_pass_enable,METH_VARARGS,"enable/disable IPv6 pass"},
    {"route_tcp_mss_set",(PyCFunction)router_route_tcp_mss_set,METH_VARARGS,"set tcp mss value"},
    {"dns_drop_no_system_enable",(PyCFunction)router_dns_drop_no_system_enable,METH_VARARGS,"enable/disable no system dns"},
    //
    {"icmpv6_dns_set",(PyCFunction)router_icmpv6_dns_set,METH_VARARGS,"set ICMPv6 NDP dns option"},
    {"icmpv6_dns_unset",(PyCFunction)router_icmpv6_dns_unset,METH_NOARGS,"unset ICMPv6 NDP dns option"},
    {"icmpv6_wan_dnsserver_get",(PyCFunction)router_icmpv6_wan_dnsserver_get,METH_NOARGS,"get WAN ICMPv6 NDP dns option value"},
    //
    {"pppoe_enable",(PyCFunction)router_pppoe_enable,METH_VARARGS,"enable or disable pppoe"},
    {"pppoe_is_enabled",(PyCFunction)router_pppoe_is_enabled,METH_NOARGS,"check pppoe is enabled"},
    {"pppoe_start",(PyCFunction)router_pppoe_start,METH_NOARGS,"start pppoe"},
    {"pppoe_stop",(PyCFunction)router_pppoe_stop,METH_NOARGS,"stop pppoe"},
    {"pppoe_set_ok",(PyCFunction)router_pppoe_set_ok,METH_VARARGS,"set pppoe ok or not ok"},
    {"pppoe_data_send",(PyCFunction)router_pppoe_data_send,METH_VARARGS,"send pppoe session data"},
    {"pppoe_reset",(PyCFunction)router_pppoe_reset,METH_VARARGS,"reset pppoe session"},
    {"pppoe_force_ac_name",(PyCFunction)router_pppoe_force_ac_name,METH_VARARGS,"force pppoe ac name"},
    {"pppoe_set_service_name",(PyCFunction)router_pppoe_set_service_name,METH_VARARGS,"set pppoe service name"},
    {"pppoe_set_host_uniq",(PyCFunction)router_pppoe_set_host_uniq,METH_VARARGS,"set pppoe host uniq"},
    //
    {"port_map_add",(PyCFunction)router_port_map_add,METH_VARARGS,"port map add"},
    {"port_map_del",(PyCFunction)router_port_map_del,METH_VARARGS,"port map delete"},
    //
    {"clog_set",(PyCFunction)router_clog_set,METH_VARARGS,"set c language log path"},
    //
    {"wan_ready_ok",(PyCFunction)router_wan_ready_ok,METH_NOARGS,"check wan ready ok"},
    {"wan_ip6_ready_ok",(PyCFunction)router_wan_ip6_ready_ok,METH_VARARGS,"check ipv6 ready OK"},
    //
    //
    {"network_enable",(PyCFunction)router_network_enable,METH_VARARGS,"enable or disable network"},
    //
    {"netpkt_forward_set",(PyCFunction)router_netpkt_forward_set,METH_VARARGS,"set network packet forward"},
    {"netpkt_forward_disable",(PyCFunction)router_netpkt_forward_disable,METH_VARARGS,"disable network packet forward"},
    //
    {"sec_net_add_src",(PyCFunction)router_sec_net_add_src,METH_VARARGS,"add security network rule"},
    {"sec_net_del_src",(PyCFunction)router_sec_net_del_src,METH_VARARGS,"delete security network rule"},
    {"sec_net_add_dst",(PyCFunction)router_sec_net_add_dst,METH_VARARGS,"add dst security network rule"},
    //
    {"net_monitor_set",(PyCFunction)router_net_monitor_set,METH_VARARGS,"set network monitor"},
    //
    {"qos_set_tunnel_first",(PyCFunction)router_qos_set_tunnel_first,METH_VARARGS,"set qos tunnel traffic is first"},
    {"qos_unset_tunnel",(PyCFunction)router_qos_unset_tunnel,METH_NOARGS,"unset qos tunnel traffic is first"},
    {"qos_set_mpkt_first_size",(PyCFunction)router_qos_set_mpkt_first_size,METH_VARARGS,"set mpkt first size"},
    {"qos_add_first_host_hwaddr",(PyCFunction)router_qos_add_first_host_hwaddr,METH_VARARGS,"add host hwaddr send first for qos"},
    {"qos_del_first_host_hwaddr",(PyCFunction)router_qos_del_first_host_hwaddr,METH_VARARGS,"delete host hwaddr send first for qos"},
    //
    {"passthrough_device_add",(PyCFunction)router_passthrough_device_add,METH_VARARGS,"add passthrough device"},
    {"passthrough_device_del",(PyCFunction)router_passthrough_device_del,METH_VARARGS,"delete passthrough device"},
    {"passthrough_set_vid_for_passdev",(PyCFunction)router_passthrough_set_vid_for_passdev,METH_VARARGS,"set vlan id for passdev"},
    //
    {"nat_sessions_num_get",(PyCFunction)router_nat_sessions_num_get,METH_NOARGS,"get nat sessions"},
    //
    {"cpu_num",(PyCFunction)router_cpu_num,METH_NOARGS,"get cpu num"},
    {"bind_cpu",(PyCFunction)router_bind_cpu,METH_VARARGS,"bind process to cpu core"},
    //
    {"router_start_time",(PyCFunction)router_start_time,METH_NOARGS,"get router start time"},
    //
    {"traffic_log_enable",(PyCFunction)router_traffic_log_enable,METH_VARARGS,"disable/enable traffic log"},

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
    routerMethods,
    NULL,
    NULL,
    NULL,
    NULL
};

static PyObject *
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
    PyModule_AddIntMacro(m,IXC_FLAG_SRC_FILTER);
    PyModule_AddIntMacro(m,IXC_FLAG_ROUTE_FWD);
    PyModule_AddIntMacro(m,IXC_FLAG_TRAFFIC_LOG);

    PyModule_AddIntMacro(m,IXC_NETIF_LAN);
    //
    PyModule_AddIntMacro(m,IXC_NETIF_WAN);
    //
    PyModule_AddIntMacro(m,IXC_NETIF_PASS);


    PyModule_AddIntMacro(m,IXC_SEC_NET_ACT_DROP);
    PyModule_AddIntMacro(m,IXC_SEC_NET_ACT_ACCEPT);

    PyModule_AddIntMacro(m,IXC_PASSTHROUGH_DEV_MAX);

    return m;
}

static void ixc_exit(void);

/// 发送PPPoE数据包到Python
int ixc_router_pppoe_session_send(unsigned short protocol,unsigned short length,void *data)
{
    PyObject *pfunc,*result,*args;

    pfunc=PyObject_GetAttrString(py_helper_instance,"pppoe_session_handle");
    if(NULL==pfunc){
        DBG("cannot found python function pppoe_session_handle\r\n");
        return -1;
    }

    args=Py_BuildValue("(iy#)",protocol,data,length);
    result=PyObject_CallObject(pfunc, args);

    if(NULL==result){
        PyErr_Print();
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(args);
    Py_XDECREF(result);

    return 0;
}

/// 通知函数
int ixc_router_tell(const char *content)
{
    PyObject *pfunc,*result,*args;

    pfunc=PyObject_GetAttrString(py_helper_instance,"tell");
    if(NULL==pfunc){
        DBG("cannot found python function tell\r\n");
        return -1;
    }

    args=Py_BuildValue("(s)",content);
    result=PyObject_CallObject(pfunc, args);

    if(NULL==result){
        PyErr_Print();
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(args);
    Py_XDECREF(result);

    return 0;
}

void ixc_router_exit(void)
{
    ixc_exit();
}

void ixc_router_md5_calc(void *data,int size,unsigned char *res)
{
    PyObject *pfunc,*result,*args;
    Py_ssize_t rsize;
    const char *md5_val;
    
    pfunc=PyObject_GetAttrString(py_helper_instance,"calc_md5");
    if(NULL==pfunc){
        DBG("cannot found python function calc_md5\r\n");
        return;
    }

    args=Py_BuildValue("(y#)",data,size);
    result=PyObject_CallObject(pfunc, args);

    if(NULL==result){
        PyErr_Print();
    }

    PyArg_ParseTuple(result,"y#",&md5_val,&rsize);

    if(rsize!=16){
        STDERR("wrong python return value length\r\n");
    }else{
        memcpy(res,md5_val,16);
    }

    Py_XDECREF(pfunc);
    Py_XDECREF(result);
    Py_XDECREF(args);
}

static void ixc_init_coredump(void)
{
    struct rlimit limit;
    int err;

    bzero(&limit,sizeof(struct rlimit));

    limit.rlim_cur=RLIM_INFINITY;
    limit.rlim_max=RLIM_INFINITY;

    err=setrlimit(RLIMIT_CORE,&limit);
    if(0!=err){
        STDERR("cannot set core dump\r\n");
    }

    return;
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
    //ev_set_uninit(&ixc_ev_set);
    rpc_delete();
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

static int ixc_rpc_fn_req(const char *name,void *arg,unsigned short arg_size,void *result,unsigned short *res_size)
{
    PyObject *res=NULL,*pfunc,*args;
    int is_error;
    Py_ssize_t size;
    const char *data;

    args=Py_BuildValue("(sy#)",name,arg,arg_size);

    pfunc=PyObject_GetAttrString(py_helper_instance,"rpc_fn_call");
    //DBG_FLAGS;
    res=PyObject_CallObject(pfunc, args);
    //DBG_FLAGS;

    if(NULL==res){
        Py_XDECREF(pfunc);
        sprintf(result,"system error for call function %s",name);
        *res_size=strlen(result);
        return RPC_ERR_OTHER;
    }
    // 此处解析Python调用结果
    PyArg_ParseTuple(res,"iy#",&is_error,&data,&size);
    *res_size=size;
    memcpy(result,data,*res_size);

    Py_XDECREF(pfunc);
    Py_XDECREF(args);
    Py_XDECREF(res);

    return is_error;
}

/// 设置运行环境
static void ixc_set_run_env(char *argv[])
{
    //wchar_t *program = Py_DecodeLocale(argv[0], NULL);

    strcpy(pid_path,"/tmp/ixcsys/router/router_core.pid");

    if(realpath(argv[0],run_dir)==NULL){
        STDERR("cannot get run path\r\n");
        exit(EXIT_FAILURE);
    }
    
    dirname(run_dir);

    strcpy(rpc_path,"/tmp/ixcsys/router/rpc.sock");
/*
#if PY_MINOR_VERSION >= 11
    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.program_name=program;
#else
    Py_SetProgramName(program);
#endif**/
}

static int ixc_init_python(int debug)
{
    PyObject *py_module=NULL,*cls,*v,*args,*pfunc;
    char py_module_dir[8192];

    sprintf(py_module_dir,"%s/../../",run_dir);
    
    PyImport_AppendInittab("router", &PyInit_router);
    Py_Initialize();
   
    py_add_path(py_module_dir);

    // 加载Python路由助手模块
    py_module=py_module_load("ixc_syscore.router._ixc_router_helper");
    //PyErr_Print();

    if(NULL==py_module){
        PyErr_Print();
        STDERR("cannot load python route_helper module\r\n");
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
    
    if(ixc_qos_have_data()){
        ixc_ev_set.wait_timeout=0;
    }else{
        ixc_ev_set.wait_timeout=IXC_IO_WAIT_TIMEOUT;
    }
   
    if(now-loop_time_up<30) return;

    // 每隔30s调用一次python循环
    loop_time_up=now;
    ixc_python_loop();
}


static void ixc_start(int debug)
{
    int rs;

    if(!access(pid_path,F_OK)){
        STDERR("process ixc_router_core exists\r\n");
        return;
    }

    ixc_init_coredump();

    loop_time_up=time(NULL);

    // 开启了coredump没必要捕获段错误
    //signal(SIGSEGV,ixc_signal_handle);
    signal(SIGINT,ixc_signal_handle);

    run_start_time=time(NULL);

    // 注意这里需要最初初始化以便检查环境
    rs=ixc_init_python(debug);
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

    rs=sysloop_init();
    if(rs<0){
        STDERR("cannot init sysloop\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_traffic_log_init();
    if(rs<0){
        STDERR("cannot init traffic_log\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_sec_net_init();
    if(rs<0){
        STDERR("cannot init sec net\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_g_init();
    if(rs<0){
        STDERR("cannot init global\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_nat66_init();
    if(rs<0){
        STDERR("cannot init nat66\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_mbuf_init(1024);
    if(rs<0){
        STDERR("cannot init mbuf\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_port_map_init();
    if(rs<0){
        STDERR("cannot init port_map\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_ip6sec_init();
    if(rs<0){
        STDERR("cannot init ip6sec\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_nat_init();
    if(rs<0){
        STDERR("cannot init nat\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_addr_map_init();
    if(rs<0){
        STDERR("cannot init addr map\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_qos_init();
    if(rs<0){
        STDERR("cannot init qos\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_route_init();
    if(rs<0){
        STDERR("cannot init route\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_src_filter_init();
    if(rs<0){
        STDERR("cannot init src filter\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_pppoe_init();
    if(rs<0){
        STDERR("cannot init pppoe\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_ip_init();
    if(rs<0){
        STDERR("cannot init IP\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_ip6_init();
    if(rs<0){
        STDERR("cannot init IPv6\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_icmpv6_init();
    if(rs<0){
        STDERR("cannot init ICMPv6\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_ipunfrag_init();
    if(rs<0){
        STDERR("cannot init ipunfrag\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_npfwd_init(&ixc_ev_set);
    if(rs<0){
        STDERR("cannot init npfwd\r\n");
        exit(EXIT_SUCCESS);
    }
    
    rs=rpc_create(&ixc_ev_set,rpc_path,ixc_rpc_fn_req);
    if(rs<0){
        STDERR("cannot create rpc\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_passthrough_init();
    if(rs<0){
        STDERR("cannot passthrough init\r\n");
        exit(EXIT_SUCCESS);
    }

    rs=ixc_netif_init(&ixc_ev_set);
    if(rs<0){
        STDERR("cannot init netif\r\n");
        exit(EXIT_SUCCESS);
    }
    // 内存缓存
    rpc_session_pre_alloc_set(4);
  
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
