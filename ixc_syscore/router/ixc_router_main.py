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
import ixc_syscore.router.handlers.tundev as tundev
import ixc_syscore.router.handlers.pfwd as pfwd

import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging

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

    __TUN_NAME = None

    __router = None
    __debug = None

    __if_lan_fd = None
    __if_wan_fd = None
    __tun_fd = None

    __lan_configs = None
    __wan_configs = None

    __is_linux = None
    # 是否告知系统管理进程
    __is_notify_sysadm_proc = None

    __lan_manage_addr = None
    __lan_manage_addr6 = None

    __scgi_fd = None

    __info_file = None

    __pfwd_fd = None

    __lan_local_link_ip6addr = None
    __wan_local_link_ip6addr = None

    def _write_ev_tell(self, fd: int, flags: int):
        if flags:
            self.add_evt_write(fd)
        else:
            self.remove_evt_write(fd)

    def _recv_from_proto_stack(self, if_type: int, ipproto: int, flags: int, byte_data: bytes):
        """从协议栈接收链路层数据或者IP数据包
        :param if_type:链路层协议,0表示IP数据包,该数值是一个主机序
        :param ipproto:IP协议号
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

    def load_wan_configs(self):
        path = "%s/wan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__wan_configs = conf.ini_parse_from_file(path)

    def save_wan_configs(self):
        path = "%s/wan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

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
    def lan_local_link_ip6addr(self):
        return self.__lan_local_link_ip6addr

    @property
    def wan_local_link_ip6addr(self):
        return self.__wan_local_link_ip6addr

    def release(self):
        if os.path.isfile(self.__info_file): os.remove(self.__info_file)
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

        if self.__tun_fd > 0:
            self.router.tundev_delete()
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
        self.__tun_fd = -1
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
        gw_addr = self.parse_ipaddr_format(lan_ifconfig["gw_addr"])
        hwaddr = lan_ifconfig["hwaddr"]
        manage_addr = self.parse_ipaddr_format(lan_ifconfig["manage_addr"])

        if not gw_addr:
            raise SystemExit("wrong IP address format")
        if not manage_addr:
            raise SystemExit("please set manage address")

        ip, prefix = gw_addr

        if prefix > 32 or prefix < 1:
            raise ValueError("wrong IP address prefix")
        if not netutils.is_ipv4_address(ip):
            raise ValueError("wrong IPv4 address format")

        self.__lan_manage_addr = manage_addr[0]
        self.__lan_manage_addr6 = "::1"

        byte_ip = socket.inet_pton(socket.AF_INET, ip)

        self.__if_lan_fd, self.__LAN_NAME = self.__router.netif_create(self.__LAN_NAME, router.IXC_NETIF_LAN)

        self.router.netif_set_hwaddr(router.IXC_NETIF_LAN, netutils.ifaddr_to_bytes(hwaddr))
        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, False)

        self.create_handler(-1, tapdev.tapdevice, self.__if_lan_fd, router.IXC_NETIF_LAN)

        if self.is_linux:
            self.linux_br_create(self.__LAN_BR_NAME, [lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ip link set %s promisc on" % lan_phy_ifname)
            os.system("ip link set %s up" % lan_phy_ifname)
            # 设置桥接网卡IP地址
            os.system("ip addr add %s/%d dev %s" % (manage_addr[0], manage_addr[1], self.__LAN_BR_NAME))

        else:
            self.__LAN_BR_NAME = self.freebsd_br_create([lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ifconfig %s promisc" % lan_phy_ifname)
            os.system("ifconfig %s up" % lan_phy_ifname)

    def start_wan(self):
        self.load_wan_configs()

        wan_configs = self.__wan_configs
        ip_cfg = wan_configs["ipv4"]

        wan_public = self.__wan_configs["public"]
        wan_phy_ifname = wan_public["phy_ifname"]
        wan_ifhwaddr = wan_public["hwaddr"]
        nat_enable = bool(int(ip_cfg["nat_enable"]))

        self.__if_wan_fd, self.__WAN_NAME = self.__router.netif_create(self.__WAN_NAME, router.IXC_NETIF_WAN)
        self.router.netif_set_hwaddr(router.IXC_NETIF_WAN, netutils.ifaddr_to_bytes(wan_ifhwaddr))

        if nat_enable: self.router.nat_set(True, 0, False)

        self.create_handler(-1, tapdev.tapdevice, self.__if_wan_fd, router.IXC_NETIF_WAN)

        if self.is_linux:
            self.linux_br_create(self.__WAN_BR_NAME, [wan_phy_ifname, self.__WAN_NAME, ])
            os.system("ip link set %s promisc on" % wan_phy_ifname)
            os.system("ip link set %s up" % wan_phy_ifname)
        else:
            pass

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def start_local(self):
        rs = self.router.tundev_create("ixclocal")
        self.__tun_fd, self.__TUN_NAME = rs
        self.create_handler(-1, tundev.tundevice, self.__tun_fd)

        # 设置本机器的默认路由指向
        os.system("ip route add default dev %s" % self.__TUN_NAME)

    def get_fwd_instance(self):
        """获取重定向类实例
        :return:
        """
        return self.get_handler(self.__pfwd_fd)

    def init_func(self, debug):
        self.__debug = debug
        self.__if_lan_fd = -1
        self.__if_wan_fd = -1
        self.__tun_fd = -1
        self.__router = router.router(self._recv_from_proto_stack, self._write_ev_tell)

        self.__WAN_BR_NAME = "ixcwanbr"
        self.__LAN_BR_NAME = "ixclanbr"

        self.__LAN_NAME = "ixclan"
        self.__WAN_NAME = "ixcwan"

        self.__wan_configs = {}
        self.__is_linux = sys.platform.startswith("linux")
        self.__is_notify_sysadm_proc = False
        self.__scgi_fd = -1
        self.__pfwd_fd = -1

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))
        self.__info_file = "%s/../syscall/ipconf.json" % os.getenv("IXC_MYAPP_TMP_DIR")

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

        signal.signal(signal.SIGSEGV, self.__mem_error)

        self.start_lan()
        self.start_wan()
        self.start_local()

        self.__pfwd_fd = self.create_handler(-1, pfwd.pfwd)

        self.start_scgi()

    def notify_sysadm_proc(self):
        path = "%s/../syscall/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")
        pid = proc.get_pid(path)

        if pid < 0: return
        self.__is_notify_sysadm_proc = True

        o = {
            "ip": self.__lan_manage_addr,
            "ipv6": self.__lan_manage_addr6
        }

        s = json.dumps(o)
        with open(self.__info_file, "w") as f: f.write(s)
        f.close()

        os.kill(pid, signal.SIGUSR1)

    def myloop(self):
        if not self.__is_notify_sysadm_proc:
            self.notify_sysadm_proc()

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

    def __mem_error(self, signum, frame):
        raise SystemError("Segmentation fault")


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

    __start_service(debug)


if __name__ == '__main__': main()
