#!/usr/bin/env python3

import sys, os, signal, time, importlib, struct, socket, json
import dns.resolver

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.lib.netutils as netutils

from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syscore.proxy.pylib.base_proto.utils as proto_utils
import ixc_syscore.proxy.pylib.crypto.utils as crypto_utils
import ixc_syscore.proxy.handlers.tunnel as tunnel

PID_FILE = "%s/proc_vpn.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service():
    cls = service()

    try:
        cls.ioloop()
    except KeyboardInterrupt:
        cls.release()
    except:
        cls.release()
        logging.print_error()

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __conf_path = None

    __conn_fd = None
    __fwd_fd = None
    __configs = None
    __session_id = None

    __tcp_crypto = None
    __udp_crypto = None

    __crypto_configs = None
    __server_ip = None
    __consts = None
    __rand_key = None
    __enable = None

    def init_func(self, debug):
        global_vars["ixcsys.proxy_vpn"] = self

        self.__debug = debug
        self.__conf_path = "%s/vpn.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__configs = {}
        self.__conn_fd = -1
        self.__enable = False

        RPCClient.wait_processes(["router", "proxy", ])
        self.load_configs()

        self.create_poll()
        self.reset()

    def reset(self):
        if bool(int(self.configs["connection"]["enable"])):
            self.__enable = True
            self.start()
        else:
            self.__enable = False

    def start(self):
        conn = self.__configs["connection"]
        m = "ixc_syscore.proxy.pylib.crypto.%s" % conn["crypto_module"]
        try:
            self.__tcp_crypto = importlib.import_module("%s.%s_tcp" % (m, conn["crypto_module"]))
            self.__udp_crypto = importlib.import_module("%s.%s_udp" % (m, conn["crypto_module"]))
        except ImportError:
            print("cannot found tcp or udp crypto module")
            sys.exit(-1)

        crypto_fpath = "%s/%s.json" % (os.getenv("IXC_MYAPP_CONF_DIR"), conn["crypto_module"])
        if not os.path.isfile(crypto_fpath):
            print("crypto configfile not exists")
            sys.exit(-1)
        try:
            crypto_configs = proto_utils.load_crypto_configfile(crypto_fpath)
        except:
            print("crypto configfile should be json file")
            sys.exit(-1)

        self.__crypto_configs = crypto_configs

    def myloop(self):
        pass

    @property
    def https_configs(self):
        configs = self.__configs.get("tunnel_over_https", {})
        enable_https_sni = bool(int(configs.get("enable_https_sni", 0)))
        https_sni_host = configs.get("https_sni_host", "")
        strict_https = bool(int(configs.get("strict_https", "0")))

        pyo = {
            "url": configs.get("url", "/"),
            "auth_id": configs.get("auth_id", "ixcsys"),
            "enable_https_sni": enable_https_sni,
            "https_sni_host": https_sni_host,
            "strict_https": strict_https,
        }

        return pyo

    @property
    def configs(self):
        return self.__configs

    def conn_cfg_update(self, dic: dict):
        fpath = "%s/vpn.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        conf.save_to_ini(dic, fpath)
        self.load_configs()
        self.reset()

    @property
    def session_id(self):
        if not self.__session_id:
            connection = self.__configs["connection"]
            username = connection["username"]
            passwd = connection["password"]

            self.__session_id = proto_utils.gen_session_id(username, passwd)

        return self.__session_id

    def load_configs(self):
        self.__configs = conf.ini_parse_from_file(self.__conf_path)

    def release(self):
        if self.__conn_fd > 0:
            self.delete_handler(self.__conn_fd)
            self.__conn_fd = -1

    def handle_msg_from_tunnel(self, session_id: bytes, action: int, message: bytes):
        if not self.__enable: return

        if session_id != self.__session_id:
            logging.print_error("wrong session_id from server")
            self.delete_handler(self.__conn_fd)
            return

        # 只支持IP数据包
        if action != proto_utils.ACT_IPDATA: return
        ip_ver = (message[0] & 0xf0) >> 4
        if ip_ver not in (4, 6,): return

    def send_msg_to_tunnel(self, action: int, message: bytes):
        if not self.__enable: return
        if not self.handler_exists(self.__conn_fd):
            self.__open_tunnel()
        if not self.handler_exists(self.__conn_fd): return

        if action != proto_utils.ACT_IPDATA:
            self.get_handler(self.__conn_fd).send_msg_to_tunnel(self.session_id, action, message)
            return

        ip_ver = (message[0] & 0xf0) >> 4
        if ip_ver not in (4, 6,): return

        if ip_ver == 4:
            host = socket.inet_ntop(socket.AF_INET, message[16:20])
        else:
            host = socket.inet_ntop(socket.AF_INET6, message[24:40])

        handler = self.get_handler(self.__conn_fd)
        handler.send_msg_to_tunnel(self.session_id, action, message)

    def __open_tunnel(self):
        conn = self.__configs["connection"]
        host = conn["host"]
        port = int(conn["port"])
        enable_ipv6 = bool(int(conn["enable_ipv6"]))
        conn_timeout = int(conn["conn_timeout"])
        tunnel_type = conn["tunnel_type"]
        redundancy = bool(int(conn.get("udp_tunnel_redundancy", 1)))
        over_https = bool(int(conn.get("tunnel_over_https", 0)))

        is_udp = False

        enable_heartbeat = bool(int(conn.get("enable_heartbeat", 0)))
        heartbeat_timeout = int(conn.get("heartbeat_timeout", 15))
        if heartbeat_timeout < 10:
            raise ValueError("wrong heartbeat_timeout value from config")

        if tunnel_type.lower() == "udp":
            handler = tunnel.udp_tunnel
            crypto = self.__udp_crypto
            is_udp = True
        else:
            handler = tunnel.tcp_tunnel
            crypto = self.__tcp_crypto

        if conn_timeout < 120:
            raise ValueError("the conn timeout must be more than 120s")

        if enable_heartbeat and conn_timeout - heartbeat_timeout < 30:
            raise ValueError("the headerbeat_timeout value wrong")

        kwargs = {"conn_timeout": conn_timeout, "is_ipv6": enable_ipv6, "enable_heartbeat": enable_heartbeat,
                  "heartbeat_timeout": heartbeat_timeout, "host": host}

        if not is_udp:
            kwargs["tunnel_over_https"] = over_https

        if tunnel_type.lower() == "udp": kwargs["redundancy"] = redundancy

        self.__conn_fd = self.create_handler(-1, handler, crypto, self.__crypto_configs, **kwargs)

        rs = self.get_handler(self.__conn_fd).create_tunnel((host, port,))
        if not rs:
            self.delete_handler(self.__conn_fd)

    def tunnel_conn_fail(self):
        self.__conn_fd = -1

    def get_server_ip(self, host):
        """获取服务器IP
        :param host:
        :return:
        """
        self.__server_ip = host

        if netutils.is_ipv4_address(host): return host
        if netutils.is_ipv6_address(host): return host

        enable_ipv6 = bool(int(self.__configs["connection"]["enable_ipv6"]))
        resolver = dns.resolver.Resolver()

        try:
            if enable_ipv6:
                rs = resolver.query(host, "AAAA")
            else:
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
        self.__server_ip = ipaddr
        if not ipaddr: return ipaddr

        return ipaddr

    @property
    def ca_path(self):
        """获取CA路径
        :return:
        """
        path = "%s/ca-bundle.crt" % os.getenv("IXC_MYAPP_CONF_DIR")
        return path

    def get_crypto_module_conf(self, name: str):
        path = "%s/vpn_%s.json" % (os.getenv("IXC_MYAPP_CONF_DIR"), name)
        if not os.path.isfile(path): return None
        if name not in crypto_utils.get_crypto_modules(): return None

        with open(path, "r") as f:
            s = f.read()
        f.close()

        return json.loads(s)

    def save_crypto_module_conf(self, name: str, dic: dict):
        if name not in crypto_utils.get_crypto_modules(): return False

        mname = "ixc_syscore.proxy.pylib.crypto.%s.check" % name
        importlib.import_module(mname)
        m = sys.modules[mname]
        if not m.check_crypto_module_config(dic): return False

        path = "%s/vpn_%s.json" % (os.getenv("IXC_MYAPP_CONF_DIR"), name)
        with open(path, "w") as f:
            f.write(json.dumps(dic))
        f.close()
        return True
