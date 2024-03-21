#!/usr/bin/env python3

import sys, os, signal, time, importlib, struct, socket, json, zlib
import dns.resolver, dns.message

### 启pyjoin JIT加速
# try:
#    import pyjion
#    pyjion.enable()
# except ImportError:
#    pass

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils
import pywind.lib.timer as timer

from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.web.route as webroute

import ixc_syscore.proxy.pylib.base_proto.utils as proto_utils
import ixc_syscore.proxy.pylib.file_parser as file_parser
import ixc_syscore.proxy.pylib.ip_match as ip_match
import ixc_syscore.proxy.pylib.crypto.utils as crypto_utils
import ixc_syscore.proxy.pylib.racs_cext as racs_cext
import ixc_syscore.proxy.pylib.base_proto.tunnel_over_http as tunnel_over_http
import ixc_syscore.proxy.handlers.tunnel as tunnel
import ixc_syscore.proxy.handlers.netpkt as netpkt
import ixc_syscore.proxy.handlers.dns_proxy as dns_proxy
import ixc_syscore.proxy.handlers.racs as racs

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_proxy_main process exists")
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


ROUTE_TIMEOUT = 480


class service(dispatcher.dispatcher):
    __conf_path = None

    __conn_fd = None
    __fwd_fd = None
    __dns_fd = None

    __debug = None
    __configs = None

    __session_id = None

    __tcp_crypto = None
    __udp_crypto = None

    __crypto_configs = None
    __server_ip = None

    __routes = None
    __static_routes = None
    __route_timer = None

    __consts = None
    __rand_key = None
    __manage_addr = None

    __dns_map = None
    __up_time = None

    __ip_match = None

    __enable = None

    __racs_configs = None
    __racs_fd = None
    __racs_byte_network_v4 = None
    __racs_byte_network_v6 = None

    # DNS查询是否故障,设置标志,防止阻塞
    __dns_query_tunnel_is_error = None
    __dns_query_racs_is_error = None

    # DNS执行重试时间
    __dns_query_tunnel_retry_up_time = None
    __dns_query_racs_retry_up_time = None

    def init_func(self, debug):
        global_vars["ixcsys.proxy"] = self

        self.__debug = debug
        self.__conf_path = "%s/proxy.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__configs = {}
        self.__routes = {}
        self.__static_routes = {}
        self.__route_timer = timer.timer()
        self.__dns_map = {}
        self.__up_time = time.time()
        self.__dns_query_tunnel_retry_up_time = time.time()
        self.__dns_query_racs_retry_up_time = time.time()
        self.__ip_match = ip_match.ip_match()
        self.__conn_fd = -1
        self.__enable = False
        self.__racs_configs = {}
        self.__racs_fd = -1
        self.__dns_query_tunnel_is_error = False
        self.__dns_query_racs_is_error = False

        RPCClient.wait_processes(["router", "DNS", ])

        while 1:
            rs = RPCClient.fn_call("router", "/config", "wan_ready_ok")
            if not rs:
                time.sleep(10)
            else:
                break
            ''''''
        self.load_configs()

        self.create_poll()
        self.start_scgi()
        self.reset()
        self.reset_racs()

    def reset(self):
        if self.__conn_fd > 0:
            self.delete_handler(self.__conn_fd)
            self.__conn_fd = -1

        if bool(int(self.configs["connection"]["enable"])):
            self.__enable = True
            self.start(self.__debug)
        else:
            self.__enable = False
            # 清除DNS规则
            RPCClient.fn_call("DNS", "/rule", "clear")
            # 关闭src filter
            RPCClient.fn_call("router", "/config", "src_filter_enable", False)
            self.del_routes()

    def start(self, debug):
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

        self.set_forward()
        self.__set_rules()

    def set_domain_rule(self):
        fpath = "%s/proxy_domain.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        try:
            rules = file_parser.parse_host_file(fpath)
            for r in rules:
                host, n = r
                if n == 0:
                    action = "encrypt"
                elif n == 1:
                    action = "proxy"
                else:
                    continue
                RPCClient.fn_call("DNS", "/rule", "add", host, action)
        except file_parser.FilefmtErr:
            logging.print_error()

    def __set_rules(self):
        RPCClient.fn_call("DNS", "/rule", "clear")
        port = RPCClient.fn_call("DNS", "/rule", "get_forward")
        RPCClient.fn_call("DNS", "/config", "forward_dns_result")

        self.get_handler(self.__dns_fd).set_forward(port)
        self.__ip_match.clear()
        self.set_domain_rule()

        fpaths = [
            "%s/pass_ip.txt" % os.getenv("IXC_MYAPP_CONF_DIR"),
            "%s/proxy_ip.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        ]
        for fpath in fpaths:
            if not os.path.isfile(fpath):
                sys.stderr.write("cannot found %s\r\n" % fpath)
                return
            ''''''
        try:
            rules = file_parser.parse_ip_subnet_file(fpaths[0])
            for subnet, prefix in rules:
                self.__ip_match.add_rule(subnet, prefix)
            rules = file_parser.parse_ip_subnet_file(fpaths[1])
            self.__set_static_ip_rules(rules)
        except file_parser.FilefmtErr:
            logging.print_error()

    def __set_static_ip_rules(self, rules):
        # nameserver = self.__configs["public"]["remote_dns"]
        # ns_is_ipv6 = netutils.is_ipv6_address(nameserver)

        # 查看新的规则
        kv_pairs_new = {}
        for subnet, prefix in rules:
            if not netutils.is_ipv6_address(subnet) and not netutils.is_ipv4_address(subnet):
                logging.print_error("wrong pre ip rule %s/%s" % (subnet, prefix,))
                continue
            is_ipv6 = netutils.is_ipv6_address(subnet)

            # 找到和nameserver冲突的路由那么跳过
            # t = netutils.calc_subnet(nameserver, prefix, is_ipv6=ns_is_ipv6)
            # if t == subnet:
            #    logging.print_error(
            #        "conflict preload ip rules %s/%s with nameserver %s" % (subnet, prefix, nameserver,)
            #    )
            #    continue

            name = "%s/%s" % (subnet, prefix,)
            kv_pairs_new[name] = (subnet, prefix, is_ipv6,)
        # 需要删除的列表
        need_dels = []
        # 需要增加的路由
        need_adds = []

        for name in kv_pairs_new:
            # 新的规则旧的没有那么就需要添加
            if name not in self.__static_routes:
                need_adds.append(kv_pairs_new[name])

        for name in self.__static_routes:
            # 旧的规则新的没有,那么就是需要删除
            if name not in kv_pairs_new:
                need_dels.append(self.__static_routes[name])

        # 删除需要删除的路由
        for subnet, prefix, is_ipv6 in need_dels:
            self.__del_route(subnet, prefix=prefix, is_ipv6=is_ipv6, is_dynamic=False)

        # 增加需要增加的路由
        for subnet, prefix, is_ipv6 in need_adds:
            self.set_route(subnet, prefix=prefix, is_ipv6=is_ipv6, is_dynamic=False)

    def auto_proxy_with_ip(self, ip: str, is_ipv6=False):
        if self.__ip_match.match(ip, is_ipv6=is_ipv6): return
        self.set_route(ip, is_ipv6=is_ipv6)

    def myloop(self):
        del_dns_list = []
        now = time.time()
        if now - self.__up_time < 3: return

        for dns_id in self.__dns_map:
            dns_info = self.__dns_map[dns_id]
            t = dns_info["time"]
            if t > 3: del_dns_list.append(dns_id)

        for dns_id in del_dns_list:
            del self.__dns_map[dns_id]

        self.__up_time = time.time()

        names = self.__route_timer.get_timeout_names()
        for name in names:
            if name in self.__routes:
                self.__del_route(name)
            ''''''
        # 检查连接是否断开,如果断开那么重新建立连接
        if self.__racs_configs["connection"]["enable"] and self.__racs_fd < 0:
            self.reset_racs()

    @property
    def https_configs(self):
        configs = self.__configs.get("tunnel_over_https", {})
        enable_https_sni = bool(int(configs.get("enable_https_sni", 0)))
        https_sni_host = configs.get("https_sni_host", "")
        strict_https = bool(int(configs.get("strict_https", "0")))
        ciphers = configs.get("ciphers", "NULL")

        if ciphers.upper() != "NULL":
            if ciphers[-1] == ",": ciphers = ciphers[0:-1]
            ciphers = ciphers.strip()
            if not ciphers:
                ciphers = "NULL"
            else:
                _list = ciphers.split(",")
                new_list = []
                for s in _list:
                    s = s.strip()
                    new_list.append(s)
                ciphers = ":".join(new_list)
            ''''''
        pyo = {
            "url": configs.get("url", "/"),
            "auth_id": configs.get("auth_id", "ixcsys"),
            "enable_https_sni": enable_https_sni,
            "https_sni_host": https_sni_host,
            "strict_https": strict_https,
            "ciphers": ciphers
        }

        return pyo

    @property
    def configs(self):
        return self.__configs

    @property
    def proxy_domain_rule_raw_get(self):
        fpath = "%s/proxy_domain.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(fpath, "r") as f:
            s = f.read()
        f.close()
        return s.encode().decode("latin1")

    @property
    def pass_ip_rule_raw_get(self):
        fpath = "%s/pass_ip.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(fpath, "r") as f:
            s = f.read()
        f.close()
        return s.encode().decode("latin1")

    @property
    def proxy_ip_rule_raw_get(self):
        fpath = "%s/proxy_ip.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(fpath, "r") as f:
            s = f.read()
        f.close()
        return s.encode().decode("latin1")

    @property
    def racs_configs(self):
        return self.__racs_configs

    def racs_cfg_update(self, cfg: dict):
        fpath = "%s/racs.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        conn = cfg["connection"]
        network = cfg["network"]

        conn["enable"] = int(conn["enable"])
        conn["enable_ip6"] = int(conn["enable_ip6"])

        network["enable_ip6"] = int(network["enable_ip6"])

        self.__dns_query_racs_is_error = False

        conf.save_to_ini(cfg, fpath)

        self.reset_racs()

    def tell_racs_close(self):
        self.__racs_fd = -1

    def load_racs_configs(self):
        fpath = "%s/racs.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        configs = conf.ini_parse_from_file(fpath)
        conn = configs["connection"]
        network = configs["network"]

        conn["enable"] = bool(int(conn["enable"]))
        conn["tunnel_type"] = conn.get("tunnel_type", "udp")
        conn["enable_ip6"] = bool(int(conn["enable_ip6"]))

        network["enable_ip6"] = bool(int(network["enable_ip6"]))

        host, prefix = netutils.parse_ip_with_prefix(network["ip_route"])

        self.__racs_byte_network_v4 = (
            socket.inet_pton(socket.AF_INET, host),
            socket.inet_pton(socket.AF_INET, netutils.ip_prefix_convert(int(prefix), is_ipv6=False))
        )

        host, prefix = netutils.parse_ip_with_prefix(network["ip6_route"])
        self.__racs_byte_network_v6 = (
            socket.inet_pton(socket.AF_INET6, host),
            socket.inet_pton(socket.AF_INET6, netutils.ip_prefix_convert(int(prefix), is_ipv6=True))
        )
        self.__racs_configs = configs

    def clear_racs_route(self):
        """清除远程访问路由
        """
        if not self.__racs_configs: return
        conn = self.__racs_configs["connection"]
        network = self.__racs_configs["network"]

        # 清除旧的路由记录
        if conn["enable"]:
            if network["enable_ip6"]:
                host, prefix = netutils.parse_ip_with_prefix(network["ip6_route"])
                RPCClient.fn_call("router", "/config", "del_route", host, prefix, is_ipv6=True)
            host, prefix = netutils.parse_ip_with_prefix(network["ip_route"])
            RPCClient.fn_call("router", "/config", "del_route", host, prefix, is_ipv6=False)
        return

    def reset_racs(self):
        now = time.time()
        self.clear_racs_route()

        if self.__racs_fd > 0:
            self.delete_handler(self.__racs_fd)
        self.__racs_fd = -1

        self.load_racs_configs()

        conn = self.__racs_configs["connection"]
        security = self.__racs_configs["security"]
        network = self.__racs_configs["network"]

        # 检查功能是否开启
        if not conn["enable"]: return

        if self.__dns_query_racs_is_error and now - self.__dns_query_racs_retry_up_time < 300: return

        self.__dns_query_racs_retry_up_time = now
        # 默认使用UDP隧道协议
        tunnel_type = conn.get("tunnel_type", "udp").lower()
        if tunnel_type not in ("tcp", "udp",):
            tunnel_type = "udp"

        if tunnel_type == "tcp":
            h = racs.tcp_tunnel
        else:
            h = racs.udp_tunnel

        if conn["enable_ip6"]:
            self.__racs_fd = self.create_handler(-1, h, (conn["host"], int(conn["port"]),), is_ipv6=True)
        else:
            self.__racs_fd = self.create_handler(-1, h, (conn["host"], int(conn["port"]),), is_ipv6=False)

        # 此处可能由于查找域名失败而无法建立隧道
        if self.__racs_fd < 0: return

        self.get_handler(self.__racs_fd).set_key(security["shared_key"])
        self.get_handler(self.__racs_fd).set_priv_key(security["private_key"])

        if network["enable_ip6"]:
            host, prefix = netutils.parse_ip_with_prefix(network["ip6_route"])
            RPCClient.fn_call("router", "/config", "add_route", host, prefix, "::", is_ipv6=True)

        host, prefix = netutils.parse_ip_with_prefix(network["ip_route"])
        RPCClient.fn_call("router", "/config", "add_route", host, prefix, "0.0.0.0", is_ipv6=False)

    def update_domain_rule(self, text: str):
        fpath = "%s/proxy_domain.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(fpath, "w") as f: f.write(text)
        f.close()
        RPCClient.fn_call("DNS", "/rule", "clear")
        self.set_domain_rule()

    def update_pass_ip_rule(self, text: str):
        fpath = "%s/pass_ip.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(fpath, "w") as f: f.write(text)
        f.close()
        self.reset()
        self.__set_rules()

    def update_proxy_ip_rule(self, text: str):
        fpath = "%s/proxy_ip.txt" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(fpath, "w") as f: f.write(text)
        f.close()
        self.reset()
        self.__set_rules()

    def conn_cfg_update(self, dic: dict):
        fpath = "%s/proxy.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        conf.save_to_ini(dic, fpath)
        self.__dns_query_tunnel_is_error = False
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
        connection = self.__configs["connection"]
        https_configs = self.__configs["tunnel_over_https"]

        if "self_no_fwd_enable" not in connection: connection["self_no_fwd_enable"] = 0
        if "ciphers" not in https_configs: https_configs["ciphers"] = "NULL"

    def get_manage_addr(self):
        ipaddr = RPCClient.fn_call("router", "/config", "manage_addr_get")

        return ipaddr

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    @property
    def manage_addr(self):
        return self.__manage_addr

    def handle_msg_from_local(self, message: bytes):
        version = (message[0] & 0xf0) >> 4
        if version not in (4, 6,): return

        if not self.racs_configs["connection"]["enable"]:
            self.send_msg_to_tunnel(proto_utils.ACT_IPDATA, message)
            return

        if version == 4:
            dst_addr = message[16:20]
            is_ipv6 = False
        else:
            dst_addr = message[24:40]
            is_ipv6 = True

        if is_ipv6 and not self.racs_configs["network"]["enable_ip6"]:
            self.send_msg_to_tunnel(proto_utils.ACT_IPDATA, message)
            return

        if is_ipv6:
            is_racs_network = racs_cext.is_same_subnet_with_msk(dst_addr, self.__racs_byte_network_v6[0],
                                                                self.__racs_byte_network_v6[1], is_ipv6)
        else:
            is_racs_network = racs_cext.is_same_subnet_with_msk(dst_addr, self.__racs_byte_network_v4[0],
                                                                self.__racs_byte_network_v4[1], is_ipv6)

        if is_racs_network:
            if self.__racs_fd > 0:
                self.get_handler(self.__racs_fd).send_msg(message)
            else:
                return
            ''''''
        else:
            self.send_msg_to_tunnel(proto_utils.ACT_IPDATA, message)

    def release(self):
        if self.__scgi_fd > 0: self.delete_handler(self.__scgi_fd)
        if self.__conn_fd > 0:
            self.delete_handler(self.__conn_fd)
            self.__conn_fd = -1
        if self.__racs_fd > 0:
            self.clear_racs_route()
            self.delete_handler(self.__racs_fd)
            self.__racs_fd = -1
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

    def del_routes(self):
        dels = []
        for name in self.__static_routes:
            r = self.__static_routes[name]
            dels.append(r)
        for host, prefix, is_ipv6 in dels:
            self.__del_route(host, prefix=prefix, is_ipv6=is_ipv6, is_dynamic=False)

        dels = []
        for host in self.__routes:
            dels.append((host, self.__routes[host]))
        for host, is_ipv6 in dels:
            self.__del_route(host, is_ipv6=is_ipv6)
        ''''''

    def send_to_local(self, message: bytes):
        ip_ver = (message[0] & 0xf0) >> 4
        if ip_ver not in (4, 6,): return
        # 检查IP数据包长度,避免程序运行出错
        if len(message) < 20: return
        if ip_ver == 4:
            p = message[9]
        else:
            p = message[6]
        self.get_handler(self.__fwd_fd).send_msg(self.__consts["IXC_NETIF_LAN"], p,
                                                 self.__consts["IXC_FLAG_ROUTE_FWD"], message)

    def handle_msg_from_tunnel(self, session_id: bytes, action: int, message: bytes):
        if not self.__enable: return

        if session_id != self.__session_id:
            logging.print_error("wrong session_id from server")
            self.delete_handler(self.__conn_fd)
            return

        # 对消息进行解压
        if action == proto_utils.ACT_ZLIB_IPDATA or action == proto_utils.ACT_ZLIB_DNS:
            try:
                message = zlib.decompress(message)
            except zlib.error:
                return

            if action == proto_utils.ACT_ZLIB_IPDATA:
                action = proto_utils.ACT_IPDATA
            else:
                action = proto_utils.ACT_DNS
            ''''''

        if action == proto_utils.ACT_IPDATA:
            ip_ver = (message[0] & 0xf0) >> 4
            if ip_ver not in (4, 6,): return
            # 检查IP数据包长度,避免程序运行出错
            if len(message) < 20: return
            if ip_ver == 4:
                p = message[9]
            else:
                p = message[6]
            self.get_handler(self.__fwd_fd).send_msg(self.__consts["IXC_NETIF_LAN"], p,
                                                     self.__consts["IXC_FLAG_ROUTE_FWD"], message)
            return
        if len(message) < 8: return
        dns_id = struct.unpack("!H", message[0:2])
        if dns_id not in self.__dns_map: return

        o = self.__dns_map[dns_id]

        # 如果DNS只走加密那么直接发送DNS数据包
        if o["action"] == "encrypt":
            self.get_handler(self.__dns_fd).send_dns_msg(message)
            del self.__dns_map[dns_id]
            return

        # 此处处理DNS消息
        try:
            msg_obj = dns.message.from_wire(message)
        except:
            return

        for rrset in msg_obj.answer:
            for cname in rrset:
                ip = cname.__str__()
                if netutils.is_ipv4_address(ip):
                    self.set_route(ip, prefix=32)
                    continue
                if netutils.is_ipv6_address(ip):
                    self.set_route(ip, prefix=128, is_ipv6=True)
                    continue
                ''''''
            ''''''
        self.get_handler(self.__dns_fd).send_dns_msg(message)
        del self.__dns_map[dns_id]

    def send_dns_request_to_tunnel(self, action: str, dns_msg: bytes):
        if not self.__enable: return
        dns_id = struct.unpack("!H", dns_msg[0:2])
        self.__dns_map[dns_id] = {"time": time.time(), "action": action}
        self.send_msg_to_tunnel(proto_utils.ACT_DNS, dns_msg)

    def send_msg_to_tunnel(self, action: int, message: bytes):
        if not self.__enable: return
        if not self.handler_exists(self.__conn_fd): self.__open_tunnel()
        if not self.handler_exists(self.__conn_fd): return

        # 压缩DNS和IPDATA数据
        if action == proto_utils.ACT_DNS:
            length = len(message)
            new_msg = zlib.compress(message)
            comp_length = len(new_msg)

            if comp_length < length:
                message = new_msg
                action = proto_utils.ACT_ZLIB_DNS
                ''''''
            ''''''
        if action != proto_utils.ACT_IPDATA:
            self.get_handler(self.__conn_fd).send_msg_to_tunnel(self.session_id, action, message)
            return

        ip_ver = (message[0] & 0xf0) >> 4
        if ip_ver not in (4, 6,): return

        try:
            if ip_ver == 4:
                host = socket.inet_ntop(socket.AF_INET, message[16:20])
            else:
                host = socket.inet_ntop(socket.AF_INET6, message[24:40])
        except:
            return

        self.__update_route_access(host)

        length = len(message)
        new_msg = zlib.compress(message)
        comp_length = len(new_msg)

        if comp_length < length:
            message = new_msg
            action = proto_utils.ACT_ZLIB_IPDATA

        handler = self.get_handler(self.__conn_fd)
        handler.send_msg_to_tunnel(self.session_id, action, message)

    def set_forward(self):
        self.__dns_fd = self.create_handler(-1, dns_proxy.dns_proxy)
        self.__rand_key = os.urandom(16)
        consts = RPCClient.fn_call("router", "/config", "get_all_consts")
        self.__fwd_fd = self.create_handler(-1, netpkt.netpkt_handler)
        port = self.get_handler(self.__fwd_fd).get_sock_port()
        self.get_handler(self.__fwd_fd).set_message_auth(self.__rand_key)

        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_ROUTE_FWD"])
        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_SRC_FILTER"])

        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_SRC_FILTER"],
                                        self.__rand_key, port)
        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_ROUTE_FWD"],
                                        self.__rand_key, port)

        RPCClient.fn_call("DNS", "/rule", "set_forward", self.get_handler(self.__dns_fd).get_port())

        self.__consts = consts
        self.__manage_addr = self.get_manage_addr()

        # 此处设置源代理
        src_filter = self.configs["src_filter"]
        enable = bool(int(src_filter["enable"]))
        ip, prefix = netutils.parse_ip_with_prefix(src_filter["ip_range"])
        ip6, prefix6 = netutils.parse_ip_with_prefix(src_filter["ip6_range"])
        protocol = src_filter["protocol"]

        RPCClient.fn_call("router", "/config", "src_filter_enable", enable)
        RPCClient.fn_call("router", "/config", "src_filter_set_ip", ip, prefix, is_ipv6=False)
        RPCClient.fn_call("router", "/config", "src_filter_set_ip", ip6, prefix6, is_ipv6=True)
        RPCClient.fn_call("router", "/config", "src_filter_set_protocols", protocol)

    def __open_tunnel(self):
        self.__session_id = None
        now = time.time()
        conn = self.__configs["connection"]
        host = conn["host"]
        port = int(conn["port"])
        enable_ipv6 = bool(int(conn["enable_ipv6"]))
        conn_timeout = int(conn["conn_timeout"])
        tunnel_type = conn["tunnel_type"]
        redundancy = bool(int(conn.get("udp_tunnel_redundancy", 1)))
        over_https = bool(int(conn.get("tunnel_over_https", 0)))
        use_https = False

        if self.__dns_query_tunnel_is_error and now - self.__dns_query_tunnel_retry_up_time < 300: return

        self.__dns_query_tunnel_retry_up_time = now
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
            if over_https:
                use_https = True
                crypto = tunnel_over_http
            ''''''

        if conn_timeout < 120:
            raise ValueError("the conn timeout must be more than 120s")

        if enable_heartbeat and conn_timeout - heartbeat_timeout < 30:
            raise ValueError("the headerbeat_timeout value wrong")

        kwargs = {"conn_timeout": conn_timeout, "is_ipv6": enable_ipv6, "enable_heartbeat": enable_heartbeat,
                  "heartbeat_timeout": heartbeat_timeout, "host": host}

        if not is_udp:
            kwargs["tunnel_over_https"] = over_https

        if tunnel_type.lower() == "udp": kwargs["redundancy"] = redundancy

        if use_https:
            self.__conn_fd = self.create_handler(-1, handler, crypto, None, **kwargs)
            self.get_handler(self.__conn_fd).set_use_http_thin_protocol(True)
        else:
            self.__conn_fd = self.create_handler(-1, handler, crypto, self.__crypto_configs, **kwargs)

        rs = self.get_handler(self.__conn_fd).create_tunnel((host, port,))
        if not rs:
            self.delete_handler(self.__conn_fd)

    def tunnel_conn_fail(self):
        RPCClient.fn_call("router", "/config", "qos_unset_tunnel")
        self.__conn_fd = -1

    def get_proxy_server_ip(self, host):
        self.__server_ip = host

        enable_ipv6 = bool(int(self.__configs["connection"]["enable_ipv6"]))
        ipaddr = self.get_server_ip(host, enable_ipv6=enable_ipv6)

        if ipaddr:
            self.__dns_query_tunnel_is_error = False
            self.__server_ip = ipaddr
            RPCClient.fn_call("router", "/config", "qos_set_tunnel_first", ipaddr, enable_ipv6)
        else:
            self.__dns_query_tunnel_is_error = True

        return ipaddr

    def get_racs_server_ip(self, host):
        enable_ipv6 = self.__racs_configs["connection"]["enable_ip6"]
        ipaddr = self.get_server_ip(host, enable_ipv6=enable_ipv6)

        if not ipaddr:
            self.__dns_query_racs_is_error = True
        else:
            self.__dns_query_racs_is_error = False

        return ipaddr

    def get_server_ip(self, host, enable_ipv6=False):
        """获取服务器IP
        :param host:
        :return:
        """
        if netutils.is_ipv4_address(host): return host
        if netutils.is_ipv6_address(host): return host

        resolver = dns.resolver.Resolver()

        resolver.timeout = 5
        resolver.lifetime = 5

        try:
            try:
                if enable_ipv6:
                    rs = resolver.resolve(host, "AAAA")
                else:
                    rs = resolver.resolve(host, "A")
                ''''''
            except AttributeError:
                try:
                    if enable_ipv6:
                        rs = resolver.query(host, "AAAA")
                    else:
                        rs = resolver.query(host, "A")
                    ''''''
                except:
                    return None
                ''''''
        except:
            return None

        ipaddr = None

        for anwser in rs:
            ipaddr = anwser.__str__()
            break
        if not ipaddr: return ipaddr
        # 检查路由是否冲突
        rs = self.__get_conflict_from_static_route(ipaddr, is_ipv6=enable_ipv6)
        # 路由冲突那么先删除路由
        if rs:
            self.__del_route(rs[0], prefix=rs[1], is_ipv6=rs[2], is_dynamic=False)
            logging.print_error("conflict route with tunnel ip,it is %s/%s" % (rs[0], rs[1],))

        if ipaddr in self.__routes:
            self.__del_route(ipaddr, is_dynamic=True, is_ipv6=enable_ipv6)

        return ipaddr

    def set_route(self, host, prefix=None, timeout=None, is_ipv6=False, is_dynamic=True):
        if host in self.__routes: return
        # 如果是服务器的地址,那么不设置路由,避免使用ip_rules规则的时候进入死循环,因为服务器地址可能不在ip_rules文件中
        if host == self.__server_ip: return

        if is_ipv6:
            if prefix is None: prefix = 128
        else:
            if prefix is None: prefix = 32

        if is_ipv6:
            n = 128
        else:
            n = 32

        # 首先查看是否已经加了永久路由
        while n > 0:
            subnet = netutils.calc_subnet(host, n, is_ipv6=is_ipv6)
            name = "%s/%s" % (subnet, n)
            n -= 1
            # 找到永久路由的记录就直接返回,避免冲突
            if name not in self.__static_routes: continue
            return

        # 调用RPC加入路由
        if is_ipv6:
            RPCClient.fn_call("router", "/config", "add_route", host, prefix, "::", is_ipv6=is_ipv6)
        else:
            RPCClient.fn_call("router", "/config", "add_route", host, prefix, "0.0.0.0", is_ipv6=is_ipv6)

        if not is_dynamic:
            name = "%s/%s" % (host, prefix,)
            self.__static_routes[name] = (host, prefix, is_ipv6,)
            return

        if not timeout: timeout = ROUTE_TIMEOUT
        self.__route_timer.set_timeout(host, timeout)
        self.__routes[host] = is_ipv6

    def __get_conflict_from_static_route(self, ipaddr, is_ipv6=False):
        """获取与static冲突的结果
        :param ipaddr:
        :param is_ipv6:
        :return:
        """
        if is_ipv6:
            n = 128
        else:
            n = 32

        rs = None

        while n > 0:
            sub = netutils.calc_subnet(ipaddr, n, is_ipv6=is_ipv6)
            name = "%s/%s" % (sub, n,)
            if name in self.__static_routes:
                rs = self.__static_routes[name]
                break
            n -= 1
        return rs

    def __del_route(self, host, prefix=None, is_ipv6=False, is_dynamic=True):
        if is_dynamic: is_ipv6 = self.__routes[host]

        if is_ipv6:
            if not prefix: prefix = 128
        else:
            if not prefix: prefix = 32

        # 此处调用RPC删除路由
        RPCClient.fn_call("router", "/config", "del_route", host, prefix, is_ipv6=is_ipv6)

        if is_dynamic:
            self.__route_timer.drop(host)
            del self.__routes[host]
        else:
            name = "%s/%s" % (host, prefix,)
            if name in self.__static_routes:
                del self.__static_routes[name]
            ''''''

    def __update_route_access(self, host, timeout=None):
        """更新路由访问时间
        :param host:
        :param timeout:如果没有指定,那么使用默认超时
        :return:
        """
        if host not in self.__routes: return
        if not timeout:
            timeout = ROUTE_TIMEOUT
        self.__route_timer.set_timeout(host, timeout)

    @property
    def ca_path(self):
        """获取CA路径
        :return:
        """
        path = "%s/data/ca-bundle.crt" % os.getenv("IXC_MYAPP_DIR")
        return path

    def get_crypto_module_conf(self, name: str):
        path = "%s/%s.json" % (os.getenv("IXC_MYAPP_CONF_DIR"), name)
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

        path = "%s/%s.json" % (os.getenv("IXC_MYAPP_CONF_DIR"), name)
        with open(path, "w") as f:
            f.write(json.dumps(dic))
        f.close()
        return True


def main():
    __helper = "ixc_syscore/proxy helper: start | stop | debug"
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
        sys.stderr = logging.stderr()
        sys.stdout = logging.stdout()
        debug = False

    __start_service(debug)


if __name__ == '__main__': main()
