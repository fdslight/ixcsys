#!/usr/bin/env python3
import os, sys, signal, json, time, multiprocessing
import dns.resolver
from cloudflare_ddns import CloudFlare

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

from pywind.global_vars import global_vars

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as cfg
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils

import ixc_syslib.pylib.logging as logging
import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.sysadm.handlers.httpd as httpd
import ixc_syscore.sysadm.pylib.power_monitor as power_monitor
import ixc_syscore.sysadm.handlers.n2n_client as n2n_client

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the sysadm process exists")
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


def cf_ddns_sync(configs: dict, debug=False):
    """cloudflare DDNS同步
    """
    try:
        cf = CloudFlare(configs["email"], configs["api_key"],
                        configs["domain"])
        cf.sync_dns_from_my_ip()
    except:
        if debug:
            print("cannot sync cloudflare DDNS")
        else:
            logging.print_error("cannot sync cloudflare DDNS")


class service(dispatcher.dispatcher):
    __httpd_fd = None
    __httpd_fd6 = None

    __httpd_ssl_fd = None
    __httpd_ssl_fd6 = None

    __debug = None

    __httpd_cfg_path = None
    __httpd_configs = None

    __scgi_fd = None

    # 是否需要重启
    __is_restart = None
    __up_time = None

    __cloudflare_ddns_cfg = None
    __cloudflare_ddns_cfg_path = None
    __ddns_up_time = None

    __file_download_cfg_path = None
    __file_download_cfg = None

    __auto_shutdown_cfg = None
    __auto_shutdown_cfg_path = None

    __power = None

    __diskless_cfg_macs_path = None
    __diskless_cfg_macs = None

    __udp_n2n_conf_path = None
    __udp_n2n_configs = None
    # 客户端到NAT服务端的映射
    __udp_n2n_fwd_tb = None
    # NAT服务端到客户端的映射
    __udp_n2n_fwd_tb_reverse = None

    __udp_n2n_fds = None

    def get_server_ip(self, host):
        """获取服务器IP
        :param host:
        :return:
        """
        if netutils.is_ipv4_address(host): return host
        if netutils.is_ipv6_address(host): return None

        resolver = dns.resolver.Resolver()

        try:
            rs = resolver.query(host, "A")
        except dns.resolver.NoAnswer:
            return None
        except dns.resolver.Timeout:
            return None
        except dns.resolver.NoNameservers:
            return None
        except:
            return None

        ipaddr = None

        for anwser in rs:
            ipaddr = anwser.__str__()
            break

        return ipaddr

    def create_udp_n2n(self):
        for k, v in self.__udp_n2n_configs.items():
            host = v["host"]
            port = int(v["port"])
            redir_host = v["redirect_host"]
            redir_port = int(v["redirect_port"])

            host = self.get_server_ip(host)
            if not host:
                logging.print_alert("wrong host value %s" % host)
                continue
            fd = self.create_handler(-1, n2n_client.n2nd, ("0.0.0.0", 0), (host, port,), (redir_host, redir_port))
            self.__udp_n2n_fds.append(fd)


    def load_configs(self):
        self.__httpd_configs = cfg.ini_parse_from_file(self.__httpd_cfg_path)
        self.load_cloudflare_ddns_cfg()
        self.load_file_download_cfg()
        self.load_auto_shutdown_cfg()
        self.load_diskless_cfg_macs()
        self.load_udp_n2n_config()

    def load_udp_n2n_config(self):
        if not os.path.isfile(self.__udp_n2n_conf_path):
            self.__udp_n2n_configs = {}
            return
        self.__udp_n2n_configs = cfg.ini_parse_from_file(self.__udp_n2n_conf_path)

    @property
    def udp_n2n_configs(self):
        return self.__udp_n2n_configs

    def reset_udp_n2n(self):
        for fd in self.__udp_n2n_fds: self.delete_handler(fd)

    def load_diskless_cfg_macs(self):
        if not os.path.isfile(self.__diskless_cfg_macs_path):
            self.__diskless_cfg_macs = {}
            return

        with open(self.__diskless_cfg_macs_path, "r") as f:
            s = f.read()
        f.close()
        self.__diskless_cfg_macs = json.loads(s)

        self.reset_diskless()

    def load_auto_shutdown_cfg(self):
        if not os.path.isfile(self.__auto_shutdown_cfg_path):
            self.__auto_shutdown_cfg = {
                "begin_hour": 0,
                "begin_min": 0,
                "end_hour": 23,
                "end_min": 59,
                "auto_shutdown_type": "network",
                "https_host": "www.cloudflare.com"
            }
        with open(self.__auto_shutdown_cfg_path, "r") as f:
            s = f.read()
        f.close()
        self.__auto_shutdown_cfg = json.loads(s)

    def save_auto_shutdown_cfg(self):
        with open(self.__auto_shutdown_cfg_path, "w") as f:
            f.write(json.dumps(self.__auto_shutdown_cfg))
        f.close()

    @property
    def auto_shutdown_cfg(self):
        return self.__auto_shutdown_cfg

    @property
    def download_cfg(self):
        return self.__file_download_cfg["config"]

    @property
    def power(self):
        return self.__power

    def load_file_download_cfg(self):
        if not os.path.isfile(self.__file_download_cfg_path):
            o = {
                "config": {
                    "dir": "/tmp",
                    "enable": 0
                }
            }
        else:
            o = cfg.ini_parse_from_file(self.__file_download_cfg_path)

        self.__file_download_cfg = o

    def save_diskless_cfg_macs(self):
        s = json.dumps(self.__diskless_cfg_macs)
        with open(self.__diskless_cfg_macs_path, "w") as f:
            f.write(s)
        f.close()

    def save_file_download_cfg(self):
        cfg.save_to_ini(self.__file_download_cfg, self.__file_download_cfg_path)

    def set_file_download(self, enable: bool, d="/tmp"):
        self.__file_download_cfg['config'] = dict(enable=int(enable), dir=d)

    def write_to_configs(self):
        pass

    def http_start(self):
        manage_addr = self.get_manage_addr()

        listen = self.__httpd_configs["listen"]
        ssl_cfg = self.__httpd_configs["ssl"]

        enable_ipv6 = bool(int(listen["enable_ipv6"]))
        enable_ssl = bool(int(listen["enable_ssl"]))

        port = int(listen["port"])

        ssl_key = ssl_cfg["key"]
        ssl_cert = ssl_cfg["cert"]

        self.__httpd_fd = self.create_handler(-1, httpd.httpd_listener, (manage_addr, port,), is_ipv6=False)
        if enable_ipv6:
            self.__httpd_fd6 = self.create_handler(-1, httpd.httpd_listener, ("::", port,), is_ipv6=True)
        if not enable_ssl: return

        self.__httpd_ssl_fd = self.create_handler(-1, httpd.httpd_listener, (manage_addr, port,), is_ipv6=False,
                                                  ssl_on=True, ssl_key=ssl_key, ssl_cert=ssl_cert)
        self.__httpd_ssl_fd6 = self.create_handler(-1, httpd.httpd_listener, ("::", port,), is_ipv6=False,
                                                   ssl_on=True, ssl_key=ssl_key, ssl_cert=ssl_cert)

    def init_func(self, debug):
        self.__httpd_fd = -1
        self.__httpd_fd6 = -1
        self.__httpd_ssl_fd = -1
        self.__httpd_ssl_fd6 = -1
        self.__debug = debug
        self.__up_time = time.time()

        self.__httpd_cfg_path = "%s/httpd.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__cloudflare_ddns_cfg_path = "%s/cloudflare_ddns.json" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__file_download_cfg_path = "%s/file_download.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__file_download_cfg = {}

        self.__auto_shutdown_cfg = {}
        self.__auto_shutdown_cfg_path = "%s/auto_shutdown.json" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__diskless_cfg_macs_path = "%s/diskless_macs.json" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__udp_n2n_configs = {}
        self.__udp_n2n_conf_path = "%s/udp_n2n_client.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__udp_n2n_fwd_tb = {}
        self.__udp_n2n_fwd_tb_reverse = {}

        self.__scgi_fd = -1
        self.__is_restart = False
        self.__ddns_up_time = time.time()

        global_vars["ixcsys.sysadm"] = self

        RPCClient.wait_processes(["router", "DHCP"])
        time.sleep(10)

        self.load_configs()
        self.create_poll()

        self.start_scgi()
        self.http_start()
        self.start_power_monitor()

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route(),
            "debug": self.__debug
        }

        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def add_to_hwaddr_to_power_monitor(self):
        fpath = "%s/wake_on_lan.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        conf = cfg.ini_parse_from_file(fpath)

        self.__power.clear()

        for name in conf:
            o = conf[name]
            if "add_to_power_ctl" not in o:
                o["add_to_power_ctl"] = 0
            add_to_power_ctl = bool(int(o['add_to_power_ctl']))
            if add_to_power_ctl: self.__power.add_hwaddr(o["hwaddr"])

    def start_power_monitor(self):
        self.__power = power_monitor.power_monitor(
            int(self.auto_shutdown_cfg["begin_hour"]),
            int(self.auto_shutdown_cfg["begin_min"]),
            int(self.auto_shutdown_cfg["end_hour"]),
            int(self.auto_shutdown_cfg["end_min"]),
            self.auto_shutdown_cfg["https_host"],
            self.get_manage_addr(),
            1999,
            self.auto_shutdown_cfg["auto_shutdown_type"]
        )
        self.add_to_hwaddr_to_power_monitor()
        self.__power.set_enable(self.auto_shutdown_cfg["enable"])

    def get_manage_addr(self):
        ipaddr = RPCClient.fn_call("router", "/config", "manage_addr_get")

        return ipaddr

    def myloop(self):
        # 这里需要等待一会儿重启,因为需要向浏览器响应信息
        now = time.time()
        if now - self.__up_time > 10 and self.__is_restart:
            self.do_restart()

        # 如果启用DDNS并且大于同步时间那么进行同步
        if self.ddns_enabled and now - self.__ddns_up_time > self.ddns_sync_interval:
            self.__ddns_up_time = now
            p = multiprocessing.Process(target=cf_ddns_sync, args=(self.cloudflare_ddns_config,),
                                        kwargs={"debug": self.debug})
            p.start()

        self.__power.loop()
        self.__up_time = time.time()

    @property
    def debug(self):
        return self.__debug

    @property
    def ddns_enabled(self):
        return self.__cloudflare_ddns_cfg["enable"]

    @property
    def ddns_sync_interval(self):
        return self.__cloudflare_ddns_cfg["sync_interval"]

    @property
    def cloudflare_ddns_config(self):
        return self.__cloudflare_ddns_cfg

    def load_cloudflare_ddns_cfg(self):
        with open(self.__cloudflare_ddns_cfg_path, "r") as f:
            s = f.read()
        f.close()
        self.__cloudflare_ddns_cfg = json.loads(s)

    def save_cloudflare_ddns_cfg(self):
        s = json.dumps(self.__cloudflare_ddns_cfg)
        with open(self.__cloudflare_ddns_cfg_path, "w") as f:
            s = f.write(s)
        f.close()

    def cloudflare_ddns_set(self, email: str, api_key: str, domain: str, sync_interval: int, enable=False):
        """设置cloudflare DDNS
        """
        self.__cloudflare_ddns_cfg = {
            "email": email,
            "api_key": api_key,
            "enable": enable,
            "sync_interval": sync_interval,
            "domain": domain
        }
        self.save_cloudflare_ddns_cfg()

    def diskless_os_cfg_get(self, hwaddr: str):
        """获取无盘的操作系统配置
        """
        return self.__diskless_cfg_macs.get(hwaddr, {})

    @property
    def diskless_cfg_macs(self):
        return self.__diskless_cfg_macs

    def reset_diskless(self):
        RPCClient.fn_call("DHCP", "/dhcp_server", "clear_boot_ext_option")

        for hwaddr in self.__diskless_cfg_macs:
            _dict = self.__diskless_cfg_macs[hwaddr]
            RPCClient.fn_call("DHCP", "/dhcp_server", "set_boot_ext_option", hwaddr, 17, _dict["root-path"])
            RPCClient.fn_call("DHCP", "/dhcp_server", "set_boot_ext_option", hwaddr, 175, "iPXE")
            RPCClient.fn_call("DHCP", "/dhcp_server", "set_boot_ext_option", hwaddr, 203, _dict["initiator-iqn"])

    def do_restart(self):
        """执行路由器重启
        :return:
        """
        # 向主进程发送信号进行重启
        fpath = "/tmp/ixcsys/ixcsys.pid"
        pid = proc.get_pid(fpath)
        os.kill(pid, signal.SIGUSR1)

    def restart(self):
        self.__up_time = time.time()
        self.__is_restart = True

    def release(self):
        if self.__scgi_fd:
            self.delete_handler(self.__scgi_fd)
            self.__scgi_fd = -1
        if self.__httpd_fd > 0:
            self.delete_handler(self.__httpd_fd)
            self.__httpd_fd = -1
        if self.__httpd_fd6 > 0:
            self.delete_handler(self.__httpd_fd6)
            self.__httpd_fd6 = -1
        if self.__httpd_ssl_fd > 0:
            self.delete_handler(self.__httpd_ssl_fd)
            self.__httpd_ssl_fd = -1
        if self.__httpd_ssl_fd6 > 0:
            self.delete_handler(self.__httpd_ssl_fd6)
            self.__httpd_ssl_fd6 = -1
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))


def main():
    __helper = "ixc_syscore/sysadm helper: start | stop | debug"

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
