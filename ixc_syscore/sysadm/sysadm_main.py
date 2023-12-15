#!/usr/bin/env python3
import os, sys, signal, json, time, multiprocessing
import dns.resolver

from cloudflare_ddns import CloudFlare

sys.path.append(os.getenv("IXC_SYS_DIR"))

import ixc_syscore.sysadm.pylib.network_shift as network_shift
import ixc_syslib.pylib.RPCClient as RPC

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
import ixc_syscore.sysadm.handlers.traffic_log as traffic_log
import ixc_syscore.sysadm.pylib.power_monitor as power_monitor
import ixc_syscore.sysadm.pylib.traffic_log as traffic_log_parser

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

    __traffic_log_fd = None
    __traffic_log_parser = None

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

    # 网络切换
    __network_shift_conf_path = None
    __network_shift_cfg = None
    __network = None
    # 网络是否工作站临时网卡上
    __network_work_on_temp = None

    # 获取全球IP地址更新时间
    __global_ip_cron_time_up = None
    __global_ip_cache = None

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

    def load_configs(self):
        self.__httpd_configs = cfg.ini_parse_from_file(self.__httpd_cfg_path)
        self.load_cloudflare_ddns_cfg()
        self.load_file_download_cfg()
        self.load_auto_shutdown_cfg()
        self.load_diskless_cfg_macs()
        self.load_network_shift_config()

    def start_network_shift(self):
        self.__network_work_on_temp = False
        self.__network = network_shift.network()

        if not self.network_shift_config["enable"]: return
        if not self.network_shift_config["is_main"]: return

        self.__network_work_on_temp = True

        configs = RPC.fn_call("router", "/config", "wan_config_get")
        if_wan_name = configs["public"]["phy_ifname"]

        # 如果是主网络那么数据恢复原先的配置
        RPC.fn_call("router", "/config", "wan_ifname_set", self.network_shift_config["device_name"])
        # 设置为DHCP模式
        RPC.fn_call("router", "/config", "internet_type_set", self.network_shift_config["internet_type"])
        RPC.fn_call("router", "/config", "config_save")

        self.network_shift_config["is_main"] = False
        self.network_shift_config["internet_type"] = "dhcp"
        self.network_shift_config["device_name"] = if_wan_name

        self.save_network_shift_conf()

    @property
    def network_is_work_on_temp(self):
        return self.__network_work_on_temp

    def load_network_shift_config(self):
        if not os.path.isfile(self.__network_shift_conf_path):
            self.__network_shift_cfg = {
                "enable": False,
                "device_name": "",
                "check_host": "",
                # 是否是主网络
                "is_main": False,
                "internet_type": ""
            }
            return

        with open(self.__network_shift_conf_path, "r") as f: s = f.read()
        f.close()

        self.__network_shift_cfg = json.loads(s)

    @property
    def network_shift_config(self):
        return self.__network_shift_cfg

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

        self.__network_shift_conf_path = "%s/network_shift.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__network_shift_cfg = None

        self.__scgi_fd = -1
        self.__traffic_log_fd = -1
        self.__traffic_log_parser = traffic_log_parser.parser()
        self.__is_restart = False
        self.__ddns_up_time = time.time()

        self.__global_ip_cron_time_up = time.time()
        self.__global_ip_cache = {"ip": "", "ip6": ""}

        global_vars["ixcsys.sysadm"] = self

        RPCClient.wait_processes(["router", "DHCP", "DNS"])
        time.sleep(10)

        self.load_configs()
        self.create_poll()

        self.start_scgi()
        self.http_start()
        self.start_traffic_log()
        self.start_power_monitor()
        self.start_network_shift()

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

    def start_traffic_log(self):
        rand_key = os.urandom(16)
        self.__traffic_log_fd = self.create_handler(-1, traffic_log.traffic_log_handler)
        port = self.get_handler(self.__traffic_log_fd).get_sock_port()
        self.get_handler(self.__traffic_log_fd).set_message_auth(rand_key)

        consts = RPCClient.fn_call("router", "/config", "get_all_consts")
        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_TRAFFIC_LOG"])
        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_TRAFFIC_LOG"],
                                        rand_key, port)
        RPCClient.fn_call("router", "/config", "traffic_log_enable", True)

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
        self.__traffic_log_parser.task_loop()

        if self.network_shift_config["enable"]:
            # 网络测试不通过直接网络切换
            if not self.__network.network_ok(self.network_shift_config["check_host"]):
                self.do_network_shift()
            ''''''
        # 定时获取全球IP地址
        self.get_self_global_ip()

        self.__up_time = time.time()

    @property
    def debug(self):
        return self.__debug

    def do_network_shift(self):
        configs = RPC.fn_call("router", "/config", "wan_config_get")
        if_wan_name = configs["public"]["phy_ifname"]
        cur_internet_type = RPC.fn_call("router", "/config", "cur_internet_type_get")

        RPC.fn_call("router", "/config", "wan_ifname_set", self.network_shift_config["device_name"])
        # 设置为DHCP模式
        RPC.fn_call("router", "/config", "internet_type_set", "dhcp")
        RPC.fn_call("router", "/config", "config_save")

        # 保留主网卡的配置
        self.network_shift_config["device_name"] = if_wan_name
        self.network_shift_config["internet_type"] = cur_internet_type
        self.network_shift_config["is_main"] = True

        self.save_network_shift_conf()
        # 重启路由器
        self.restart()

    def save_network_shift_conf(self):
        s = json.dumps(self.__network_shift_cfg)
        with open(self.__network_shift_conf_path, "w") as f: f.write(s)
        f.close()

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

    def handle_traffic_log_message(self, message: bytes):
        self.__traffic_log_parser.parse(message)

    def traffic_log_get(self):
        return self.__traffic_log_parser.traffic_log_get()

    def __get_self_global_ip(self):
        """获取自己的全球IP地址
        """
        seq = [
            "-4 'https://api.ipify.org?format=json'",
            "-6 'https://api64.ipify.org?format=json'"
        ]
        # 检查curl是否存在
        if not os.path.isfile("/usr/bin/curl"):
            return {
                "ip": "not curl for get ip",
                "ip6": "not curl for get ipv6"
            }

        addr_list = []

        for t in seq:
            cmd = "curl --connect-timeout 3 %s" % t
            with os.popen(cmd) as f:
                s = f.read()
            f.close()

            try:
                o = json.loads(s)
            except:
                logging.print_alert("server response wrong data %s for get self global ip" % s)
                continue
            if "ip" not in o:
                logging.print_alert("server response wrong data %s for get self global ip" % s)
                continue

            addr_list.append(o["ip"])

        result = {
            "ip": "",
            "ip6": ""
        }

        for ip in addr_list:
            is_ipv6 = netutils.is_ipv6_address(ip)
            is_ipv4 = netutils.is_ipv4_address(ip)

            if not is_ipv4 and not is_ipv6:
                logging.print_alert("server response wrong data for get self global ip value %s" % ip)
                continue

            if is_ipv4:
                result["ip"] = ip
            else:
                result["ip6"] = ip
            ''''''

        return result

    def get_self_global_ip(self):
        now = time.time()

        if now - self.__global_ip_cron_time_up < 60: return

        self.__global_ip_cache = self.__get_self_global_ip()
        self.__global_ip_cron_time_up = now

        return self.__global_ip_cache

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
        if self.__traffic_log_fd > 0:
            RPCClient.fn_call("router", "/config", "traffic_log_enable", True)
            self.delete_handler(self.__traffic_log_fd)
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
