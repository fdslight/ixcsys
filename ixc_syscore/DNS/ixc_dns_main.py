#!/usr/bin/env python3

import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.DNS.handlers.dns_proxyd as dns_proxyd

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_dns_main process exists")
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
    __dns_server = None
    __dns_client = None

    __dns_configs = None
    __dns_conf_path = None

    def init_func(self, *args, **kwargs):
        self.__dns_server = -1
        self.__dns_client = -1

        self.__dns_conf_path = "%s/dns.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.create_poll()
        self.wait_router_proc()

    def load_configs(self):
        self.__dns_configs = conf.ini_parse_from_file(self.__dns_conf_path)

    def wait_router_proc(self):
        """等待路由进程
        """
        while 1:
            ok = RPCClient.RPCReadyOk("router")
            if not ok:
                time.sleep(5)
            else:
                break
            ''''''
        return

    def start_dns(self):
        self.load_configs()
        manage_addr = self.get_manage_addr()
        ipv4 = self.__dns_configs["ipv4"]

        self.__dns_client = self.create_handler(-1, dns_proxyd.proxy_client, ipv4["main_dns"], ipv4["second_dns"],
                                                is_ipv6=False)
        self.__dns_server = self.create_handler(-1, dns_proxyd.proxyd, (manage_addr, 53), is_ipv6=False)

    def get_manage_addr(self):
        """获取管理地址
        """
        ipaddr = RPCClient.fn_call("router", "/runtime", "get_manage_ipaddr")

        return ipaddr

    def release(self):
        if self.__dns_server > 0: self.delete_handler(self.__dns_server)
        if self.__dns_client > 0: self.delete_handler(self.__dns_client)


def main():
    __helper = "ixc_syscore/DNS helper: start | stop | debug"
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
