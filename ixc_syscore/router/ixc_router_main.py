#!/usr/bin/env python3

import sys, os, signal, socket, json

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

from pywind.global_vars import global_vars

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils

import ixc_syscore.router.pylib.router as router
import ixc_syscore.router.handlers.tapdev as tapdev
import ixc_syscore.router.handlers.pfwd as pfwd
import ixc_syscore.router.pylib.pppoe as pppoe

import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPC

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_router process exists")
        return

    if not debug:
        pid = os.fork()
        if pid != 0: sys.exit(0)

        os.setsid()
        os.umask(0)
        pid = os.fork()

        if pid != 0: sys.exit(0)

        proc.write_pid(PID_FILE, os.getpid())

    cls = service(debug)

    try:
        cls.ioloop(debug)
    except KeyboardInterrupt:
        cls.release()
    except:
        cls.release()
        logging.print_error()

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __WAN_BR_NAME = None
    __LAN_BR_NAME = None

    __LAN_NAME = None
    __WAN_NAME = None

    __router = None
    __debug = None

    __if_lan_fd = None
    __if_wan_fd = None

    __lan_configs = None
    __wan_configs = None
    __router_configs = None
    __port_map_configs = None

    __is_linux = None
    __scgi_fd = None

    __pfwd_fd = None

    __pppoe = None
    __pppoe_enable = None
    __pppoe_user = None
    __pppoe_passwd = None

    def _tell(self, content: str):
        if content == "lcp_start":
            if self.__pppoe: self.__pppoe.start_lcp()
        if content == "lcp_stop":
            if self.__pppoe: self.__pppoe.stop_lcp()

    def _write_ev_tell(self, fd: int, flags: int):
        if flags:
            self.add_evt_write(fd)
        else:
            self.remove_evt_write(fd)

    def _recv_from_proto_stack(self, if_type: int, ipproto: int, flags: int, byte_data: bytes):
        """从协议栈接收链路层数据或者IP数据包
        :param if_type:链路层协议,
        :param ipproto:IP协议号,0表示链路层数据包
        :param flags:额外附带的标记
        :param byte_data:
        :return:
        """
        if not self.handler_exists(self.__pfwd_fd): return
        self.get_handler(self.__pfwd_fd).recv_from_netstack(if_type, ipproto, flags, byte_data)

    def send_to_proto_stack(self, if_type: int, ipproto: int, flags: int, byte_data: bytes):
        """发送链路层数据或者IP数据包到协议栈
        :param if_type:链路层协议,如果是0表示IP数据包,该数值是一个主机序
        :param ipproto,IP层协议
        :param flags: 额外的附带标志
        :param byte_data:
        :return:
        """
        self.__router.send_netpkt(if_type, ipproto, flags, byte_data)

    def load_lan_configs(self):
        path = "%s/lan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__lan_configs = conf.ini_parse_from_file(path)

    def save_lan_configs(self):
        path = "%s/lan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        conf.save_to_ini(self.__lan_configs, path)

    def load_wan_configs(self):
        path = "%s/wan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__wan_configs = conf.ini_parse_from_file(path)

    def save_wan_configs(self):
        path = "%s/wan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        conf.save_to_ini(self.__wan_configs, path)

    def load_router_configs(self):
        path = "%s/router.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__router_configs = conf.ini_parse_from_file(path)

    def load_port_map_configs(self):
        path = "%s/port_map.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(path, "r") as f: s = f.read()
        f.close()
        self.__port_map_configs = json.loads(s)

    def save_router_configs(self):
        path = "%s/router.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        conf.save_to_ini(self.__router_configs, path)

    def save_port_map_configs(self):
        path = "%s/port_map.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(path, "w") as f: f.write(json.dumps(self.__port_map_configs))
        f.close()

    def reset_port_map(self):
        for name in self.__port_map_configs:
            protocol, port, address = self.__port_map_configs[name]
            self.router.port_map_del(protocol, port)
        self.load_port_map_configs()
        for name in self.__port_map_configs:
            protocol, port, address = self.__port_map_configs[name]
            self.router.port_map_add(protocol, port, address)

    @property
    def router(self):
        return self.__router

    @property
    def is_linux(self):
        return self.__is_linux

    @property
    def lan_configs(self):
        return self.__lan_configs

    @property
    def wan_configs(self):
        return self.__wan_configs

    @property
    def router_configs(self):
        return self.__router_configs

    @property
    def port_map_configs(self):
        return self.__port_map_configs

    @property
    def debug(self):
        return self.__debug

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    def release(self):
        if self.is_linux:
            os.system("ip link set %s down" % self.__LAN_NAME)
            os.system("ip link set %s down" % self.__WAN_NAME)
            os.system("ip link set %s down" % self.__LAN_BR_NAME)
            os.system("ip link set %s down" % self.__WAN_BR_NAME)

            os.system("ip link del %s" % self.__LAN_BR_NAME)
            os.system("ip link del %s" % self.__WAN_BR_NAME)
        else:
            os.system("ifconfig %s destroy" % self.__LAN_BR_NAME)
            os.system("ifconfig %s destroy" % self.__WAN_BR_NAME)

        if self.__if_lan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_LAN)
        if self.__if_wan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_WAN)
        if self.__scgi_fd:
            self.delete_handler(self.__scgi_fd)
        if self.__pfwd_fd > 0:
            self.delete_handler(self.__pfwd_fd)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        self.__if_lan_fd = -1
        self.__if_wan_fd = -1
        self.__scgi_fd = -1
        self.__pfwd_fd = -1

    def linux_br_create(self, br_name: str, added_bind_ifs: list):
        cmds = [
            "ip link add name %s type bridge" % br_name,
            "ip link set dev %s up" % br_name,
        ]

        for cmd in cmds: os.system(cmd)
        for if_name in added_bind_ifs:
            cmd = "ip link set dev %s master %s" % (if_name, br_name,)
            os.system(cmd)

    def freebsd_br_create(self, added_bind_ifs: list):
        fd = os.popen("ifconfig bridge create")
        s = fd.read()
        fd.close()
        s = s.replace("\n", "")
        s = s.replace(" ", "")

        _list = ["ifconfig %s" % s, ]
        for name in added_bind_ifs:
            _list.append("addm %s" % name)
        _list.append("up")
        cmd = " ".join(_list)
        os.system(cmd)

        return s

    def start_lan(self):
        self.load_lan_configs()
        lan_ifconfig = self.__lan_configs["if_config"]
        lan_phy_ifname = lan_ifconfig["phy_ifname"]
        hwaddr = lan_ifconfig["hwaddr"]

        self.__if_lan_fd, self.__LAN_NAME = self.__router.netif_create(self.__LAN_NAME, router.IXC_NETIF_LAN)

        self.router.netif_set_hwaddr(router.IXC_NETIF_LAN, netutils.str_hwaddr_to_bytes(hwaddr))
        self.create_handler(-1, tapdev.tapdevice, self.__if_lan_fd, router.IXC_NETIF_LAN)

        if self.is_linux:
            self.linux_br_create(self.__LAN_BR_NAME, [lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ip link set %s promisc on" % lan_phy_ifname)
            # os.system("ip link set %s promisc on" % self.__LAN_NAME)
            os.system("ip link set %s up" % lan_phy_ifname)

        else:
            self.__LAN_BR_NAME = self.freebsd_br_create([lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ifconfig %s promisc" % lan_phy_ifname)
            # os.system("ifconfig %s promisc" % self.__WAN_NAME)
            os.system("ifconfig %s up" % lan_phy_ifname)

        lan_addr = lan_ifconfig["ip_addr"]
        manage_addr = lan_ifconfig["manage_addr"]
        mask = lan_ifconfig["mask"]

        byte_ipaddr = socket.inet_pton(socket.AF_INET, lan_addr)
        prefix = netutils.mask_to_prefix(mask, False)

        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ipaddr, prefix, False)

        if self.is_linux:
            os.system("ip -4 addr add %s/%s dev %s" % (manage_addr, prefix, self.__LAN_BR_NAME))
            os.system("ip -4 route add default via %s" % lan_addr)

        # IPv6的相关设置
        enable_static_ipv6 = bool(int(lan_ifconfig["enable_static_ipv6"]))
        enable_ipv6_pass = bool(int(lan_ifconfig["enable_ipv6_pass"]))
        enable_ipv6_security = bool(int(lan_ifconfig["enable_ipv6_security"]))
        ip6_addr, v6_prefix = netutils.parse_ip_with_prefix(lan_ifconfig["ip6_addr"])

        byte_ip6addr = socket.inet_pton(socket.AF_INET6, ip6_addr)

        if enable_static_ipv6:
            self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip6addr, int(v6_prefix),
                                     True)
        self.router.route_ipv6_pass_enable(enable_ipv6_pass)
        self.router.ip6sec_enable(enable_ipv6_security)
        self.router.src_filter_self_ip_set(manage_addr,False)

    def start_wan(self):
        self.__pppoe = pppoe.pppoe(self)
        self.load_wan_configs()

        wan_configs = self.__wan_configs
        ip_cfg = wan_configs["ipv4"]

        wan_public = self.__wan_configs["public"]
        wan_phy_ifname = wan_public["phy_ifname"]
        wan_ifhwaddr = wan_public["hwaddr"]
        ipv4 = self.__wan_configs["ipv4"]

        self.__if_wan_fd, self.__WAN_NAME = self.__router.netif_create(self.__WAN_NAME, router.IXC_NETIF_WAN)
        self.router.netif_set_hwaddr(router.IXC_NETIF_WAN, netutils.str_hwaddr_to_bytes(wan_ifhwaddr))

        self.create_handler(-1, tapdev.tapdevice, self.__if_wan_fd, router.IXC_NETIF_WAN)

        if self.is_linux:
            self.linux_br_create(self.__WAN_BR_NAME, [wan_phy_ifname, self.__WAN_NAME, ])
            os.system("ip link set %s promisc on" % wan_phy_ifname)
            os.system("ip link set %s promisc on" % self.__WAN_NAME)
            os.system("ip link set %s up" % wan_phy_ifname)
        else:
            pass

        wan_pppoe = self.__wan_configs["pppoe"]
        internet_type = self.__wan_configs["public"]["internet_type"]

        if internet_type == "pppoe":
            self.__pppoe_enable = True
        else:
            self.__pppoe_enable = False

        if self.__pppoe_enable:
            self.__pppoe_user = wan_pppoe["user"]
            self.__pppoe_passwd = wan_pppoe["passwd"]
            self.router.pppoe_enable(True)
            self.router.pppoe_start()
            return

        if internet_type.lower() != "static-ip": return
        # WAN口静态地址配置

        ip_addr = ipv4["address"]
        mask = ipv4["mask"]
        default_gw = ipv4.get("default_gw", None)

        byte_ipaddr = socket.inet_pton(socket.AF_INET, ip_addr)
        prefix = netutils.mask_to_prefix(mask, 0)

        self.router.netif_set_ip(router.IXC_NETIF_WAN, byte_ipaddr, prefix, False)
        if not default_gw: return

        byte_gw = socket.inet_pton(socket.AF_INET, default_gw)
        byte_subnet = socket.inet_pton(socket.AF_INET, "0.0.0.0")

        self.router.route_add(byte_subnet, 0, byte_gw, False)

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def set_gw_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)

        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, False)

    def get_fwd_instance(self):
        """获取重定向类实例
        :return:
        """
        return self.get_handler(self.__pfwd_fd)

    def get_manage_addr(self):
        return self.lan_configs["if_config"]["manage_addr"]

    def set_router(self):
        """对路由器进行设置
        :return:
        """
        self.load_router_configs()
        # 首先对QOS尽享设置
        qos = self.__router_configs["qos"]
        udp_udplite_first = bool(int(qos["udp_udplite_first"]))
        self.router.qos_udp_udplite_first_enable(udp_udplite_first)

    def port_map_add(self, protocol: int, port: int, address: str, alias_name: str):
        self.__port_map_configs[alias_name] = [protocol, port, address]
        self.save_port_map_configs()
        self.reset_port_map()

    def port_map_del(self, protocol: int, port: int):
        alias_name = None
        for name in self.__port_map_configs:
            p, _port, address = self.__port_map_configs[name]
            if p == protocol and _port == port:
                alias_name = name
                break
            ''''''
        if alias_name: del self.__port_map_configs[alias_name]
        self.save_port_map_configs()
        self.reset_port_map()

    def init_func(self, debug):
        self.__debug = debug
        self.__if_lan_fd = -1
        self.__if_wan_fd = -1
        self.__router = router.router(self._recv_from_proto_stack, self._write_ev_tell)
        self.__router.set_tell_fn(self._tell)

        self.__WAN_BR_NAME = "ixcwanbr"
        self.__LAN_BR_NAME = "ixclanbr"

        self.__LAN_NAME = "ixclan"
        self.__WAN_NAME = "ixcwan"

        self.__wan_configs = {}
        self.__is_linux = sys.platform.startswith("linux")
        self.__scgi_fd = -1
        self.__pfwd_fd = -1

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        if not self.debug:
            sys.stdout = logging.stdout()
            sys.stderr = logging.stderr()

            temp_dir = os.getenv("IXC_MYAPP_TMP_DIR")

            stdout_path = "%s/stdout.log" % temp_dir
            stderr_path = "%s/stderr.log" % temp_dir

            self.router.clog_set(stdout_path, stderr_path)

        # 此处检查FreeBSD是否加载了if_tap.ko模块
        if not self.is_linux:
            fd = os.popen("kldstat")
            s = fd.read()
            fd.close()
            p = s.find("if_tap.ko")
            if p < 0: os.system("kldload if_tap")

        self.create_poll()

        global_vars["ixcsys.router"] = self.__router
        global_vars["ixcsys.runtime"] = self

        self.start_lan()
        # 建议start_wan放在最后
        self.start_wan()

        self.__pfwd_fd = self.create_handler(-1, pfwd.pfwd)

        self.start_scgi()
        self.set_router()

        self.load_port_map_configs()
        self.reset_port_map()

    def myloop(self):
        if self.__pppoe_enable: self.__pppoe.loop()

        if not self.router.iowait():
            self.set_default_io_wait_time(0)
        else:
            self.set_default_io_wait_time(10)

        self.router.myloop()

    def parse_ipaddr_format(self, s: str):
        """解析例如 xxx/x格式的IP地址
        :param s:
        :return:
        """
        p = s.find("/")
        if p < 0: return None

        ip = s[0:p]
        p += 1
        try:
            r = (ip, int(s[p:]),)
        except ValueError:
            return None

        return r


def main():
    __helper = "ixc_syscore/router helper: start | stop | debug"
    if len(sys.argv) != 2:
        print(__helper)
        return

    action = sys.argv[1]
    if action not in ("start", "stop", "debug",):
        print(__helper)
        return

    if action == "stop":
        __stop_service()
        return

    if action == "debug":
        debug = True
    else:
        debug = False

    RPC.wait_proc("init")
    __start_service(debug)


if __name__ == '__main__': main()
