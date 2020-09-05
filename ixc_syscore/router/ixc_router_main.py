#!/usr/bin/env python3

import sys, os, signal, socket

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.lib.netutils as netutils

import ixc_syscore.router.pylib.router as router
import ixc_syscore.router.handlers.tapdev as tapdev

import ixc_syslib.pylib.logging as logging

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")

WAN_BR_NAME = "ixwanbr"
LAN_BR_NAME = "ixclanbr"

LAN_NAME = "ixclan"
WAN_NAME = "ixcwan"


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
    __router = None
    __debug = None

    __if_lan_fd = None
    __devname = None

    __lan_configs = None
    __wan_configs = None

    __is_linux = None

    def _write_ev_tell(self, fd: int, flags: int):
        if flags:
            self.add_evt_write(fd)
        else:
            self.remove_evt_write(fd)

    def _recv_from_proto_stack(self, byte_data: bytes, flags: int):
        """从协议栈接收消息
        """
        print(byte_data)

    def send_to_proto_stack(self, byte_data: bytes, flags: int):
        """向协议栈发送消息
        """
        self.__router.send_netpkt(byte_data, flags)

    def load_lan_configs(self):
        path = "%s/lan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__lan_configs = conf.ini_parse_from_file(path)

    def save_lan_configs(self):
        path = "%s/lan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

    @property
    def router(self):
        return self.__router

    @property
    def is_linux(self):
        return self.__is_linux

    def release(self):
        self.br_delete(LAN_BR_NAME)

        if self.__if_lan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_LAN)
        self.__if_lan_fd = -1

    def linux_br_create(self, br_name: str, added_bind_ifs: list):
        cmds = [
            "ip link add name %s type bridge" % br_name,
            "ip link set dev %s up" % br_name,
        ]

        for cmd in cmds: os.system(cmd)
        for if_name in added_bind_ifs:
            cmd = "ip link set dev %s master %s" % (if_name, br_name,)
            os.system(cmd)

    def freebsd_br_create(self, br_name: str, added_bind_ifs: list):
        pass

    def br_create(self, br_name: str, added_bind_ifs: list):
        """桥接网络创建
        :param br_name:
        :param added_bind_ifs:
        :return:
        """
        if sys.platform.startswith("linux"):
            self.linux_br_create(br_name, added_bind_ifs)
        else:
            self.freebsd_br_create(br_name, added_bind_ifs)

    def br_delete(self, br_name: str):
        """桥接网络删除
        :param br_name:
        :return:
        """
        if sys.platform.startswith("linux"):
            os.system("ip link del %s" % br_name)
        else:
            pass

    def init_func(self, debug):
        self.__debug = debug
        self.__if_lan_fd = -1
        self.__router = router.router(self._recv_from_proto_stack, self._write_ev_tell)
        self.__if_lan_fd, self.__devname = self.__router.netif_create(LAN_NAME, router.IXC_NETIF_LAN)

        self.load_lan_configs()
        self.__wan_configs = {}

        self.__is_linux = sys.platform.startswith("linux")

        self.create_poll()
        self.create_handler(-1, tapdev.tapdevice, self.__if_lan_fd, router.IXC_NETIF_LAN)

        lan_ifconfig = self.__lan_configs["if_config"]
        phy_ifname = lan_ifconfig["phy_ifname"]
        ipinfo = self.parse_ipaddr_format(lan_ifconfig["ip_addr"])

        if not ipinfo:
            raise SystemExit("wrong IP address format")
        ip, prefix = ipinfo
        if prefix > 32 or prefix < 1:
            raise ValueError("wrong IP address prefix")
        if not netutils.is_ipv4_address(ip):
            raise ValueError("wrong IPv4 address format")

        byte_ip = socket.inet_pton(socket.AF_INET, ip)
        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, False)

        self.br_create(LAN_BR_NAME, [self.__devname, phy_ifname])

        if self.is_linux:
            os.system("ip link set %s up" % phy_ifname)
            os.system("ip link set %s promisc on" % phy_ifname)
            os.system("ip link set %s promisc on" % LAN_BR_NAME)
        else:
            os.system("ifconfig %s up" % phy_ifname)

    def myloop(self):
        pass

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

    __start_service(debug)


if __name__ == '__main__': main()
