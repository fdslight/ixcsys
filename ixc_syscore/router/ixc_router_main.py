#!/usr/bin/env python3
import pickle
import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

from pywind.global_vars import global_vars

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi
import pywind.lib.crpc as crpc
import pywind.lib.netutils as netutils

import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging

import ixc_syscore.router.handlers.conn_mon as conn_mon_handler

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
    __debug = None

    __is_linux = None
    __scgi_fd = None

    __network_status = None
    __net_status_up_time = None

    __chk_host_info = None
    __chk_net_try_count = None
    __is_pppoe_dial = None

    __auto_set_ip6_mng_addr_up_time = None
    __ip6_mng_addr = None

    def load_chk_host_info(self):
        ok, chk_net_info = self.router_runtime_fn_call("wan_pppoe_chk_net_info_get")
        try:
            enable = bool(int(chk_net_info['enable']))
        except ValueError:
            enable = False

        if not enable:
            self.__chk_host_info = None
            return

        host = chk_net_info['host']
        try:
            port = int(chk_net_info['port'])
        except ValueError:
            enable = False
            logging.print_alert("wrong wan pppoe check host config value for port")

        if port < 1:
            logging.print_alert("wrong wan pppoe check host config value for port")
            enable = False

        is_ipv6 = False
        if netutils.is_ipv6_address(host):
            is_ipv6 = True
        if not is_ipv6 and not netutils.is_ipv4_address(host):
            enable = False
            logging.print_alert("wrong wan pppoe check host config value for host")

        if not enable:
            self.__chk_host_info = None
            return
        self.__chk_host_info = (host, port, is_ipv6,)

    def report_network_status(self, is_ok: bool):
        if not is_ok:
            logging.print_alert(
                "try connect %s %s fail for network test" % (self.__chk_host_info[0], self.__chk_host_info[1]))
            self.__chk_net_try_count += 1
        else:
            logging.print_alert(
                "try connect %s %s OK for network test" % (self.__chk_host_info[0], self.__chk_host_info[1]))
            self.__chk_net_try_count = 0

        self.__network_status = is_ok

    def clear_os_route(self, is_ipv6=False):
        """清除系统的路由表
        """
        if is_ipv6:
            fdst = os.popen("ip -6 route")
        else:
            fdst = os.popen("ip route")

        __list = []
        for line in fdst:
            line = line.replace("\n", "")
            line = line.replace("\r", "")
            p = line.find("dev")
            if p < 1: continue
            __list.append(line[0:p].strip())

        for x in __list:
            if is_ipv6:
                cmd = "ip -6 route del %s" % x
            else:
                cmd = "ip route del %s" % x
            os.system(cmd)

    @property
    def is_linux(self):
        return self.__is_linux

    @property
    def debug(self):
        return self.__debug

    def router_runtime_fn_call(self, fname: str, *args, **kwargs):
        client = crpc.RPCClient(self.rpc_sock_path)
        is_error, msg = client.fn_call(fname, *args, **kwargs)

        return is_error, pickle.loads(msg)

    def check_network_status(self):
        """检查网络状态
        """
        # 未设置那么不检查
        now = time.time()
        # 未连接成功,增加频率
        if self.__chk_net_try_count > 0:
            timeout = 30
        else:
            timeout = 600
        if now - self.__net_status_up_time < timeout: return
        self.__net_status_up_time = now

        is_err, is_enabled = self.router_runtime_fn_call("pppoe_is_enabled")
        if not is_enabled: return

        self.load_chk_host_info()
        if not self.__chk_host_info: return
        # 检查wan准备成功之后再联
        is_err, ok = self.router_runtime_fn_call("wan_ready_ok")
        if not ok: return

        host, port, is_ipv6 = self.__chk_host_info

        if self.__chk_net_try_count > 3:
            # 超过3次重置为默认状态,然后重新pppoe拨号
            self.__network_status = True
            self.__chk_net_try_count = 0
            logging.print_alert("because of cannot server %s %s,pppoe will re-dial" % (host, port))
            self.router_runtime_fn_call("pppoe_force_re_dial")
            return

        self.create_handler(-1, conn_mon_handler.conn_mon_client, host, port, is_ipv6=is_ipv6)

    def release(self):
        if self.__scgi_fd:
            self.delete_handler(self.__scgi_fd)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        os.system("%s/ixc_router_core stop" % os.getenv("IXC_MYAPP_DIR"))
        self.__scgi_fd = -1

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def init_func(self, debug):
        self.__debug = debug
        self.__scgi_fd = -1
        self.__network_status = True
        self.__net_status_up_time = time.time()
        self.__auto_set_ip6_mng_addr_up_time = time.time()
        self.__ip6_mng_addr = ""
        self.__chk_net_try_count = 0
        self.__is_pppoe_dial = False

        RPC.wait_proc("init")

        self.clear_os_route()
        self.clear_os_route(is_ipv6=True)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        os.system("%s/ixc_router_core start" % os.getenv("IXC_MYAPP_DIR"))

        # 等待router_core核心启动完成
        time.sleep(20)

        if not self.debug:
            sys.stdout = logging.stdout()
            sys.stderr = logging.stderr()

        self.create_poll()

        global_vars["ixcsys.runtime"] = self

        self.start_scgi()

    @property
    def rpc_sock_path(self):
        return "/tmp/ixcsys/router/rpc.sock"

    def auto_set_ipv6_mngaddr(self):
        now = time.time()
        if now - self.__auto_set_ip6_mng_addr_up_time < 10: return
        self.__auto_set_ip6_mng_addr_up_time = now

        cmd = "ip addr show ixclanbr | grep  inet6 | grep mng"
        mng_ip6addr = None
        fdst = os.popen(cmd)
        _list = []

        for line in fdst:
            line = line.strip()
            line = line.replace("\n", "")
            _list.append(line.lower())
        fdst.close()
        if not _list: return

        for s in _list:
            p = s.find("dep")
            # 检查地址是否被弃用
            if p >= 0: continue
            s = s.split(" ")[1]
            p = s.find("/")

            mng_ip6addr = s[0:p]
            break

        if not mng_ip6addr: return
        if mng_ip6addr != self.__ip6_mng_addr:
            self.router_runtime_fn_call("manage_addr_set", mng_ip6addr, is_ipv6=True)
            self.__ip6_mng_addr = mng_ip6addr
        return

    def myloop(self):
        self.check_network_status()
        self.auto_set_ipv6_mngaddr()


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
