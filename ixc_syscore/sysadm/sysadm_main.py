#!/usr/bin/env python3
import os, sys, signal, json, time, multiprocessing

from cloudflare_ddns import CloudFlare

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

from pywind.global_vars import global_vars

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as cfg
import pywind.web.handlers.scgi as scgi

import ixc_syslib.pylib.logging as logging
import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.sysadm.handlers.httpd as httpd
import ixc_syscore.sysadm.handlers.cloud_service as cloud_service
import ixc_syscore.sysadm.pylib.power_monitor as power_monitor

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

    __cloudservice_cfg_path = None
    __cloudservice_cfg = None

    __power = None

    # 云服务连接是否正常
    __cloudservice_conn_ok = None

    __cloud_service_fd = None

    def load_configs(self):
        self.__httpd_configs = cfg.ini_parse_from_file(self.__httpd_cfg_path)
        self.load_cloudflare_ddns_cfg()
        self.load_file_download_cfg()
        self.load_auto_shutdown_cfg()
        self.load_cloudservice_cfg()

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

    @property
    def cloud_service_cfg(self):
        return self.__cloudservice_cfg

    @property
    def cloud_service_device_id(self):
        return self.__cloudservice_cfg["device_id"]

    @property
    def cloud_service_key(self):
        return self.__cloudservice_cfg["key"]

    def reset_cloud_service(self):
        if self.__cloud_service_fd > 0:
            self.delete_handler(self.__cloud_service_fd)
            self.__cloud_service_fd = -1

        if not self.__cloudservice_cfg["enable"]: return

        self.__cloud_service_fd = self.create_handler(-1, cloud_service.cloud_service_client, "cloud.ixcsys.com", 443)

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

    def load_cloudservice_cfg(self):
        if not os.path.isfile(self.__cloudservice_cfg_path):
            self.__cloudservice_cfg = {
                "enable": False,
                "device_id": "",
                "key": ""
            }
            return

        with open(self.__cloudservice_cfg_path, "r") as f:
            s = f.read()
        f.close()
        self.__cloudservice_cfg = json.loads(s)

    def save_cloudservice_cfg(self):
        s = json.dumps(self.__cloudservice_cfg)
        with open(self.__cloudservice_cfg_path, "w") as f:
            f.write(s)
        f.close()

    def save_file_download_cfg(self):
        cfg.save_to_ini(self.__file_download_cfg, self.__file_download_cfg_path)

    def set_file_download(self, enable: bool, d="/tmp"):
        self.__file_download_cfg["config"] = {
            "enable": int(enable),
            "dir": d
        }

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
        self.__cloud_service_fd = -1
        self.__debug = debug
        self.__up_time = time.time()

        self.__httpd_cfg_path = "%s/httpd.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__cloudflare_ddns_cfg_path = "%s/cloudflare_ddns.json" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__file_download_cfg_path = "%s/file_download.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__file_download_cfg = {}

        self.__auto_shutdown_cfg = {}
        self.__auto_shutdown_cfg_path = "%s/auto_shutdown.json" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__cloudservice_cfg_path = "%s/cloud_service.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__cloudservice_cfg = {}

        self.__scgi_fd = -1
        self.__is_restart = False
        self.__ddns_up_time = time.time()

        self.__cloudservice_conn_ok = False

        global_vars["ixcsys.sysadm"] = self

        RPCClient.wait_processes(["router"])
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
    def cloud_service_status(self):
        return self.__cloudservice_conn_ok

    def set_cloud_service_status(self, ok: bool):
        """设置云服务状态
        """
        self.__cloudservice_conn_ok = ok

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
        if self.__cloud_service_fd > 0:
            self.delete_handler(self.__cloud_service_fd)
            self.__cloud_service_fd = -1
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
