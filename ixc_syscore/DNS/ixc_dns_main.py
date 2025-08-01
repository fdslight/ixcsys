#!/usr/bin/env python3
import socket, zlib
import sys, os, signal, time, struct, json, pickle
import dns.message

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
import ixc_syslib.pylib.dns_utils as dns_utils

import ixc_syscore.DNS.handlers.dns_proxyd as dns_proxyd
import ixc_syscore.DNS.pylib.rule as rule
import ixc_syscore.DNS.pylib.os_resolv as os_resolv
import ixc_syscore.DNS.pylib.sec_rule as sec_rule
import ixc_syscore.DNS.pylib.ip_match as ip_match
import ixc_syscore.DNS.pylib.DNSCache as DNSCache

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
        logging.print_error(debug=debug)

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __dns_server = None
    __dns_client = None

    __dns_server6 = None
    __dns_client6 = None

    __dns_configs = None
    __dns_conf_path = None

    # 加快查找速度
    __sec_rules_dict = None
    __sec_rule_path = None

    # WAN到LAN的DNS ID映射
    __id_wan2lan = None
    __matcher = None

    __scgi_fd = None
    __cur_dns_id = None

    # 是否重定向DNS结果
    __forward_result = None

    __wan_ok = None

    __up_dns_record_time = None
    __up_wan_ready_time = None
    __up_autoset_icmpv6_dns_time = None
    __from_dhcpv6_dns = None
    __dhcpv6_dns_a = None
    __dhcpv6_dns_b = None
    # 自动检查os resolv时间
    __up_check_os_resolv_time = None
    # IPv6管理地址
    __ip6_mngaddr = None
    # IPv4管理地址
    __ip_mngaddr = None

    __hosts_fpath = None
    __hosts = None

    __ip_match = None
    __route_timer = None

    # 是否开启安全DNS
    __enable_sec_dns = None
    # 安全DNS重定向端口
    __sec_dns_forward_port = None
    # 通信key
    __sec_dns_forward_key = None
    # 不使用安全DNS的域名列表
    __no_use_sec_dns_domains = None

    __router_wan_configs = None
    __read_pppoe_dns_time = None

    __dns_cache = None

    def init_func(self, *args, **kwargs):
        global_vars["ixcsys.DNS"] = self

        self.__dns_server = -1
        self.__dns_client = -1

        self.__dns_server6 = -1
        self.__dns_client6 = -1

        self.__dns_conf_path = "%s/dns.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__sec_rules_dict = {}
        self.__sec_rule_path = "%s/sec_rules.txt" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__id_wan2lan = {}

        self.__matcher = rule.matcher()

        self.__up_dns_record_time = time.time()
        self.__up_wan_ready_time = time.time()
        self.__up_autoset_icmpv6_dns_time = time.time()
        self.__from_dhcpv6_dns = False
        self.__dhcpv6_dns_a = ""
        self.__dhcpv6_dns_b = ""
        self.__up_check_os_resolv_time = time.time()

        self.__scgi_fd = -1
        self.__cur_dns_id = 1
        self.__forward_result = False
        self.__wan_ok = False

        # 这里必须设置为字符串空值,用于比较,如果设置为None,类型不一致比较会出错
        self.__ip6_mngaddr = ""

        self.__hosts_fpath = "%s/hosts.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__hosts = {}
        self.__ip_match = ip_match.ip_match()
        self.__route_timer = timer.timer()

        self.__enable_sec_dns = False
        self.__sec_dns_forward_port = 0
        self.__sec_dns_forward_key = os.urandom(4)
        self.__no_use_sec_dns_domains = {}

        self.__dns_cache = DNSCache.DNSCache()

        RPCClient.wait_processes(["router", ])

        wan_configs = RPCClient.fn_call("router", "/config", "wan_config_get")
        self.__router_wan_configs = wan_configs
        self.__read_pppoe_dns_time = time.time()

        self.create_poll()
        self.start_dns()
        self.start_scgi()
        self.add_ns_os_resolv()

    def is_pppoe_dial(self):
        """是否是PPPoE拨号
        """
        wan_pub = self.__router_wan_configs["public"]
        if wan_pub["internet_type"] != "pppoe": return False
        return True

    def set_no_proxy_ips(self, ip_list: str):
        """加入IP匹配规则
        """
        self.__ip_match.clear()
        for subnet, prefix in ip_list:
            self.__ip_match.add_rule(subnet, prefix)

    def set_route(self, host: str, is_ipv6=False):
        if is_ipv6:
            RPCClient.fn_call("router", "/config", "add_route", host, 128, "::", is_ipv6=is_ipv6)
        else:
            RPCClient.fn_call("router", "/config", "add_route", host, 32, "0.0.0.0", is_ipv6=is_ipv6)
        ''''''

    def get_ipv6_mngaddr(self):
        cmd = "ip addr show ixclanbr | grep  inet6 | grep mng"
        mng_ip6addr = None
        fdst = os.popen(cmd)
        _list = []

        for line in fdst:
            line = line.strip()
            line = line.replace("\n", "")
            _list.append(line.lower())
        fdst.close()
        if not _list: return None

        for s in _list:
            p = s.find("dep")
            # 检查地址是否被弃用
            if p >= 0: continue
            s = s.split(" ")[1]
            p = s.find("/")

            mng_ip6addr = s[0:p]
            break

        return mng_ip6addr

    def auto_set_ipv6_dns(self):
        """设置IPv6 DNS"""
        ip6_mngaddr = self.get_ipv6_mngaddr()

        ip6_cfg = self.configs["ipv6"]
        enable_auto = bool(int(ip6_cfg["enable_auto"]))

        if not ip6_mngaddr:
            if self.__dns_server6 >= 0:
                self.delete_handler(self.__dns_server6)
            self.__dns_server6 = -1
            return

        # RPCClient.fn_call("router", "/config", "manage_addr_set", ip6_mngaddr, is_ipv6=True)

        if self.__ip6_mngaddr != ip6_mngaddr:
            if self.__dns_server6 >= 0:
                self.delete_handler(self.__dns_server6)
            self.__dns_server6 = self.create_handler(-1, dns_proxyd.proxyd, (ip6_mngaddr, 53, 0, 0), is_ipv6=True)
            if self.__dns_server6 < 0:
                logging.print_alert("cannot create dns server socket for IPv6")
                return
            self.__ip6_mngaddr = ip6_mngaddr
        RPCClient.fn_call("router", "/config", "icmpv6_dns_set", socket.inet_pton(socket.AF_INET6, ip6_mngaddr))

        if not enable_auto: return

        dns_a, dns_b = RPCClient.fn_call("router", "/config", "icmpv6_wan_dnsserver_get")

        ip6_ns1 = ""
        ip6_ns2 = ""

        if dns_a != bytes(16):
            ip6_ns1 = socket.inet_ntop(socket.AF_INET6, dns_a)
        if dns_b != bytes(16):
            ip6_ns2 = socket.inet_ntop(socket.AF_INET6, dns_b)

        # 如果是链路本地地址,清空DNS
        if ip6_ns1:
            if ip6_ns1[0].lower() == 'f':
                ip6_ns1 = ""
            ''''''
        if ip6_ns2:
            if ip6_ns2[0].lower() == 'f':
                ip6_ns2 = ""
            ''''''
        if ip6_ns1 == "" and ip6_ns2 == "" and not self.__from_dhcpv6_dns:
            RPCClient.fn_call("router", "/config", "icmpv6_dns_unset")

        if self.__from_dhcpv6_dns:
            ip6_ns1 = self.__dhcpv6_dns_a
            ip6_ns2 = self.__dhcpv6_dns_b
        self.set_nameservers(ip6_ns1, ip6_ns2, is_ipv6=True)

    def rule_forward_set(self, port: int):
        self.get_handler(self.__dns_client).set_forward_port(port)

    def load_configs(self):
        self.__dns_configs = conf.ini_parse_from_file(self.__dns_conf_path)
        ip4_cfg = self.__dns_configs["ipv4"]
        ip6_cfg = self.__dns_configs["ipv6"]

        if "public" not in self.__dns_configs: self.__dns_configs["public"] = {}

        pub = self.__dns_configs["public"]

        if "enable_auto" not in ip4_cfg: ip4_cfg["enable_auto"] = "1"
        if "enable_auto" not in ip6_cfg: ip6_cfg["enable_auto"] = "1"
        if "enable_ipv6_dns_drop" not in pub: pub["enable_ipv6_dns_drop"] = "0"
        if "enable_dns_no_system_drop" not in pub: pub["enable_dns_no_system_drop"] = "0"
        if "dns_cache_timeout" not in pub: pub["dns_cache_timeout"] = "60"

        # 如果开启了丢弃,那么执行
        if bool(int(pub["enable_dns_no_system_drop"])):
            RPCClient.fn_call("router", "/config", "dns_drop_no_system_enable", True, is_ipv6=False)
            RPCClient.fn_call("router", "/config", "dns_drop_no_system_enable", True, is_ipv6=True)
        ''''''

    def load_sec_rules(self):
        sec_rules = sec_rule.parse_from_file(self.__sec_rule_path)
        for rule in sec_rules:
            self.__sec_rules_dict[rule] = None
            self.matcher.add_rule(rule, "drop", None)
        ''''''

    def load_hosts(self):
        default_conf = {"A": {}, "AAAA": {}}
        if not os.path.isfile(self.__hosts_fpath):
            conf = default_conf
        else:
            with open(self.__hosts_fpath, "r") as f:
                s = f.read()
            f.close()
            try:
                dic = json.loads(s)
                conf = dic
            except:
                conf = default_conf
            ''''''
        if not isinstance(conf, dict): conf = default_conf
        if "A" not in conf: conf["A"] = {}
        if "AAAA" not in conf: conf["AAAA"] = {}

        self.__hosts = conf

    def hosts_modify(self, host, addr, is_ipv6=False):
        if not host: return False
        # 地址不存在那么就删除记录
        if not addr:
            if is_ipv6:
                dic = self.__hosts["AAAA"]
            else:
                dic = self.__hosts["A"]
            if host in dic: del dic[host]
            return True
        ''''''
        if not netutils.is_ipv4_address(addr) and not netutils.is_ipv6_address(addr):
            return False

        if netutils.is_ipv6_address(addr) and not is_ipv6:
            return False

        if is_ipv6:
            dic = self.__hosts["AAAA"]
        else:
            dic = self.__hosts["A"]

        dic[host] = addr
        return True

    @property
    def hosts(self):
        return self.__hosts

    def save_hosts(self):
        s = json.dumps(self.__hosts)
        with open(self.__hosts_fpath, "w") as f: f.write(s)
        f.close()

    def hosts_get(self, host, is_ipv6=False):
        if is_ipv6:
            dic = self.__hosts["AAAA"]
        else:
            dic = self.__hosts["A"]

        return dic.get(host, None)

    def start_dns(self):
        self.load_configs()
        self.load_sec_rules()
        self.load_hosts()

        manage_addr = self.get_manage_addr()
        ipv4 = self.__dns_configs["ipv4"]
        ipv6 = self.__dns_configs["ipv6"]

        self.__dns_client = self.create_handler(-1, dns_proxyd.proxy_client, ipv4["main_dns"], ipv4["second_dns"],
                                                is_ipv6=False)
        self.__dns_client6 = self.create_handler(-1, dns_proxyd.proxy_client, ipv6["main_dns"], ipv6["second_dns"],
                                                 is_ipv6=True)
        self.__dns_server = self.create_handler(-1, dns_proxyd.proxyd, (manage_addr, 53), is_ipv6=False)

        pub = self.__dns_configs["public"]
        try:
            cache_timeout = int(pub['dns_cache_timeout'])
        except ValueError:
            cache_timeout = 60
        self.__dns_cache.set_timeout(cache_timeout)

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route(),
            # 处理有些大数据比较耗费时间,增加连接超时时间
            "timeout": 120
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def get_manage_addr(self):
        """获取管理地址
        """
        if self.__ip_mngaddr: return self.__ip_mngaddr

        self.__ip_mngaddr = RPCClient.fn_call("router", "/config", "manage_addr_get")

        return self.__ip_mngaddr

    def get_dns_id(self):
        dns_id = self.__cur_dns_id
        self.__cur_dns_id += 1
        # 此处重置DNS ID
        if self.__cur_dns_id > 0xfffe: self.__cur_dns_id = 1

        return dns_id

    def send_to_dnsserver(self, message: bytes, is_ipv6=False, is_secdns_server=False):
        """发送到DNS服务器
        """
        # 如果开启了安全DNS,那么把数据发送到安全DNS
        if self.__enable_sec_dns and not is_secdns_server:
            self.get_handler(self.__dns_client).send_forward_msg2(message, self.__sec_dns_forward_port,
                                                                  self.__sec_dns_forward_key)
            return
        ''''''
        if is_ipv6 and self.__dns_client6 < 0: return
        if not is_ipv6 and self.__dns_client < 0: return

        if is_ipv6:
            fd = self.__dns_client6
        else:
            fd = self.__dns_client

        self.get_handler(fd).send_request_msg(message)

    def handle_msg_from_dnsserver(self, message: bytes, from_cache=False):
        """处理来自于DNS服务器的消息
        """
        dns_id, = struct.unpack("!H", message[0:2])
        # 找不到映射记录那么直接删除
        if dns_id not in self.__id_wan2lan: return
        o = self.__id_wan2lan[dns_id]
        is_ipv6 = o["is_ipv6"]

        if is_ipv6:
            fd = self.__dns_server6
        else:
            fd = self.__dns_server

        o = self.__id_wan2lan[dns_id]
        x_dns_id = o["id"]
        new_msg = b"".join([struct.pack("!H", x_dns_id), message[2:]])

        # if not o["from_forward"] and self.__forward_result:
        try:
            msg_obj = dns.message.from_wire(new_msg)
        except:
            del self.__id_wan2lan[dns_id]
            return
        for rrset in msg_obj.answer:
            for cname in rrset:
                ip = cname.__str__()
                is_ipv6 = False
                if netutils.is_ipv4_address(ip):
                    flags = True
                elif netutils.is_ipv6_address(ip):
                    flags = True
                    is_ipv6 = True
                else:
                    flags = False
                if not flags: continue
                host = self.__id_wan2lan[dns_id]['host']

                # 如果来自于非缓存响应那么缓存DNS记录
                if host is not None and not from_cache:
                    r_type = DNSCache.A_RECORD
                    if is_ipv6: r_type = DNSCache.AAAA_RECORD
                    self.__dns_cache.set_cache_record(host, ip, _type=r_type)
                if self.__ip_match.match(ip, is_ipv6=is_ipv6) and not o["from_forward"]: continue
                action = o['action']
                if action is None: continue
                if action != "proxy": continue
                # DNS自动设置路由后告知proxy程序,由代理程序管理路由
                # self.set_route(ip, is_ipv6=is_ipv6)
                # 报告是需要走代理的IP,这里考虑缓存问题,需要向proxy报告
                msg = {
                    "action": "proxy_ip_report",
                    "priv_data": None,
                    "message": (ip, is_ipv6,)
                }
                if self.__forward_result:
                    self.get_handler(self.__dns_client).send_forward_msg(pickle.dumps(msg))
                    logging.print_info("notify proxy for ip address %s" % ip)
                ''''''
            ''''''
        if self.handler_exists(fd): self.get_handler(fd).send_msg(new_msg, o["address"])
        # 此处删除记录
        del self.__id_wan2lan[dns_id]

    def handle_msg_from_dnsclient(self, from_fd, message: bytes, address: tuple, is_ipv6=False):
        """处理来自于DNS客户端的消息
        """
        if len(message) < 15: return

        dns_id, = struct.unpack("!H", message[0:2])
        new_dns_id = self.get_dns_id()

        if new_dns_id < 0:
            logging.print_error("cannot get DNS ID for DNS proxy")
            return
        try:
            msg_obj = dns.message.from_wire(message)
        except:
            return

        _list = [struct.pack("!H", new_dns_id), message[2:]]
        new_msg = b"".join(_list)

        self.__id_wan2lan[new_dns_id] = {"id": dns_id, "address": address, "is_ipv6": is_ipv6,
                                         "time": time.time(), "from_forward": False, "host": None, "action": None, }

        questions = msg_obj.question
        if len(questions) != 1:
            self.send_to_dnsserver(new_msg, is_ipv6=is_ipv6)
            return

        q = questions[0]
        host = b".".join(q.name[0:-1]).decode("iso-8859-1")

        # 检查是否开启丢弃DNSv6请求
        if self.enable_drop_dnsv6():
            if dns_utils.is_aaaa_request(message):
                drop_msg = dns_utils.build_dns_no_such_name_response(dns_id, host, is_ipv6=True)
                self.get_handler(from_fd).send_msg(drop_msg, address)
                del self.__id_wan2lan[new_dns_id]
                return
            ''''''
        # 检查是否是路由器内置的域名
        if host == "router.ixcsys.com":
            if dns_utils.is_a_request(message):
                local_msg = dns_utils.build_dns_addr_response(dns_id, host, self.get_manage_addr(), is_ipv6=False)
                self.get_handler(from_fd).send_msg(local_msg, address)
            # 内置域名IPv6请求丢弃
            if dns_utils.is_aaaa_request(message):
                drop_msg = dns_utils.build_dns_no_such_name_response(dns_id, host, is_ipv6=True)
                self.get_handler(from_fd).send_msg(drop_msg, address)
            del self.__id_wan2lan[new_dns_id]
            return

        if dns_utils.is_aaaa_request(message):
            local_rr = self.hosts_get(host, is_ipv6=True)
            if local_rr is not None:
                local_msg = dns_utils.build_dns_addr_response(dns_id, host, local_rr, is_ipv6=True)
                self.get_handler(from_fd).send_msg(local_msg, address)
                del self.__id_wan2lan[new_dns_id]
                return
            ''''''
        if dns_utils.is_a_request(message):
            local_rr = self.hosts_get(host, is_ipv6=False)
            if local_rr is not None:
                local_msg = dns_utils.build_dns_addr_response(dns_id, host, local_rr, is_ipv6=False)
                self.get_handler(from_fd).send_msg(local_msg, address)
                del self.__id_wan2lan[new_dns_id]
                return
            ''''''
        # WAN无连接允许本地hosts映射
        if not self.__wan_ok:
            del self.__id_wan2lan[new_dns_id]
            return

        self.__id_wan2lan[new_dns_id]['host'] = host
        match_rs = self.__matcher.match(host)

        logging.print_info("DNS_QUERY: %s from %s" % (host, address[0]))
        is_secdns_server = False
        # 如果域名在非使用安全DNS的域名当中,强制不使用匹配规则
        if host in self.__no_use_sec_dns_domains:
            logging.print_info("security DNS domain is %s" % host)
            is_secdns_server = True
            match_rs = None

        if match_rs is None:
            sent_ok = self.send_dns_resp_from_cache(new_dns_id, host, message)
            if sent_ok: return
            self.send_to_dnsserver(new_msg, is_ipv6=is_ipv6, is_secdns_server=is_secdns_server)
            return

        action = match_rs["action"]
        # 如果规则为丢弃那么直接丢弃该DNS请求
        if action == "drop":
            flags = False
            is_aaaa = False
            if dns_utils.is_aaaa_request(message):
                is_aaaa = True
                flags = True
            elif dns_utils.is_a_request(message):
                is_aaaa = False
                flags = True
            else:
                pass

            if flags:
                drop_msg = dns_utils.build_dns_no_such_name_response(dns_id, host, is_ipv6=is_aaaa)
                self.get_handler(from_fd).send_msg(drop_msg, address)

            logging.print_info("DNS_QUERY_DROP: %s from %s" % (host, address[0]))

            del self.__id_wan2lan[new_dns_id]
            return
        # 发送DNS数据到其他应用程序,如果找不到文件号那么丢弃数据包
        if self.__dns_client < 0:
            del self.__id_wan2lan[new_dns_id]
            return

        msg = {
            "action": action,
            "priv_data": match_rs["priv_data"],
            "message": new_msg
        }

        self.__id_wan2lan[new_dns_id]["from_forward"] = True
        self.__id_wan2lan[new_dns_id]["action"] = action

        sent_ok = self.send_dns_resp_from_cache(new_dns_id, host, message)
        if sent_ok: return

        self.get_handler(self.__dns_client).send_forward_msg(pickle.dumps(msg))

    def send_dns_resp_from_cache(self, dns_id, host, message):
        r_type = None
        is_aaaa = False
        if dns_utils.is_aaaa_request(message):
            is_aaaa = True
            r_type = DNSCache.AAAA_RECORD
        if dns_utils.is_a_request(message):
            r_type = DNSCache.A_RECORD

        if r_type is None: return False

        record = self.__dns_cache.record_get(host, _type=r_type)

        if record is None: return False

        resp_msg = dns_utils.build_dns_addr_response(dns_id, host, record['address'], is_ipv6=is_aaaa)
        self.handle_msg_from_dnsserver(resp_msg, from_cache=True)
        logging.print_info("From DNS Cache for Host %s" % host)

        return True

    @property
    def matcher(self):
        return self.__matcher

    @property
    def configs(self):
        return self.__dns_configs

    @property
    def sec_rules(self):
        sec_rules = []

        for key in self.__sec_rules_dict: sec_rules.append(key)

        return sec_rules

    def is_auto(self, is_ipv6=False):
        if is_ipv6:
            cfg = self.configs["ipv6"]
        else:
            cfg = self.configs["ipv4"]

        return bool(int(cfg["enable_auto"]))

    def enable_drop_dnsv6(self):
        """是否开启了丢弃DNSv6报文
        """
        pub = self.configs["public"]

        return bool(int(pub["enable_ipv6_dns_drop"]))

    def set_drop_dnsv6_enable(self, enable: bool):
        """开启或者关闭DNSv6请求
        """
        pub = self.configs["public"]
        if enable:
            pub["enable_ipv6_dns_drop"] = "1"
        else:
            pub["enable_ipv6_dns_drop"] = "0"
        ''''''

    def dns_no_system_drop_enable(self, enable: bool):
        pub = self.configs["public"]
        if enable:
            RPCClient.fn_call("router", "/config", "dns_drop_no_system_enable", True, is_ipv6=False)
            RPCClient.fn_call("router", "/config", "dns_drop_no_system_enable", True, is_ipv6=True)
            pub["enable_dns_no_system_drop"] = "1"
        else:
            RPCClient.fn_call("router", "/config", "dns_drop_no_system_enable", False, is_ipv6=False)
            RPCClient.fn_call("router", "/config", "dns_drop_no_system_enable", False, is_ipv6=True)
            pub["enable_dns_no_system_drop"] = "0"
        return

    def get_nameservers(self, is_ipv6=False):
        if is_ipv6:
            return self.get_handler(self.__dns_client6).get_nameservers()
        else:
            return self.get_handler(self.__dns_client).get_nameservers()

    def set_nameservers(self, ns1: str, ns2: str, is_ipv6=False):
        if is_ipv6:
            self.get_handler(self.__dns_client6).set_nameservers(ns1, ns2)
        else:
            self.get_handler(self.__dns_client).set_nameservers(ns1, ns2)

    def set_ip6_nameservers_from_dhcpv6(self, ns1: str, ns2: str):
        self.__from_dhcpv6_dns = True
        self.__dhcpv6_dns_a = ns1
        self.__dhcpv6_dns_b = ns2
        # 获取不到地址,那么认为dhcpv6获取不到DNS地址
        if ns1 == "" and ns2 == "":
            self.__from_dhcpv6_dns = False
        self.set_nameservers(ns1, ns2, is_ipv6=True)

    def forward_dns_result(self, enable: bool):
        self.__forward_result = enable

    def get_forward(self):
        return self.get_handler(self.__dns_client).get_port()

    def add_sec_rule(self, rule: str):
        if rule in self.__sec_rules_dict:
            return
        self.__sec_rules_dict[rule] = None
        self.matcher.add_rule(rule, "drop", None)

    def add_sec_rules(self, rules: list):
        """批量加入rules
        """
        for rule in rules: self.add_sec_rule(rule)

    def del_sec_rule(self, rule: str):
        if rule not in self.__sec_rules_dict: return

        del self.__sec_rules_dict[rule]

        self.matcher.del_rule(rule)

    def del_sec_rules(self, rules: list):
        for rule in rules: self.del_sec_rule(rule)
        if not rules:
            rules = self.sec_rules
            for rule in rules: self.del_sec_rule(rule)
        return

    def sec_rules_modify(self, rules: list):
        added_list = []
        dels_list = []
        tmp_dict = {}

        for rule in rules:
            tmp_dict[rule] = None
            if rule in self.__sec_rules_dict:
                continue
            added_list.append(rule)
            ''''''
        old_rules = self.sec_rules
        for rule in old_rules:
            if rule in tmp_dict:
                continue
            else:
                dels_list.append(rule)
            ''''''
        for rule in added_list:
            self.add_sec_rule(rule)
        for rule in dels_list:
            self.del_sec_rule(rule)

    def sec_rules_modify_with_raw(self, text: bytes, is_compressed=False):
        """传递未经处理的文本的原始规则
        """
        if is_compressed:
            try:
                text = zlib.decompress(text)
            except:
                return
            ''''''
        s = text.decode('iso-8859-1')
        _list = s.split("\n")
        results = []

        for s in _list:
            s = s.replace("\r", "")
            s = s.replace("\t", "")
            s = s.replace(" ", "")
            s = s.strip()
            if not s: continue
            if s[0] == "#": continue
            results.append(s)

        self.sec_rules_modify(results)

    def sec_rules_modify_with_fpath(self, fpath: str):
        if not os.path.isfile(fpath): return
        with open(fpath, "r", errors='ignore') as f:
            s = f.read()
        f.close()
        self.sec_rules_modify_with_raw(s.encode("iso-8859-1"), is_compressed=False)

    def rule_clear(self):
        # 清除所有clear
        self.__matcher.clear()
        # 重新加载内部clear
        self.load_sec_rules()

    @property
    def sec_dns_forward_port(self):
        return self.__sec_dns_forward_port

    def enable_sec_dns(self, enable: bool):
        self.__enable_sec_dns = enable

    def is_enabled_sec_dns(self):
        return self.__enable_sec_dns

    def set_sec_dns_forward(self, port: int, key: bytes):
        self.__sec_dns_forward_port = port
        self.__sec_dns_forward_key = key

    def add_sec_dns_domains(self, domains: list):
        for host in domains:
            if host not in self.__no_use_sec_dns_domains:
                self.__no_use_sec_dns_domains[host] = None
            ''''''
        return

    def del_sec_dns_domains(self, domains: list):
        for host in domains:
            if host in self.__no_use_sec_dns_domains:
                del self.__no_use_sec_dns_domains[host]
            ''''''
        return

    def save_configs(self):
        conf.save_to_ini(self.__dns_configs, self.__dns_conf_path)
        self.save_sec_rules()
        self.save_hosts()

    def save_sec_rules(self):
        sec_rule.save_to_file(self.__sec_rules_dict, self.__sec_rule_path)

    def set_dns_cache_timeout(self, seconds: int):
        pub = self.__dns_configs["public"]
        pub["dns_cache_timeout"] = seconds

        logging.print_info("set DNS Cache Timeout to %s" % seconds)
        return self.__dns_cache.set_timeout(seconds)

    def clear_dns_cache(self):
        logging.print_info("clear DNS Cache")
        self.__dns_cache.clear_all_records()

    def release(self):
        if self.__scgi_fd > 0: self.delete_handler(self.__scgi_fd)
        if self.__dns_server > 0: self.delete_handler(self.__dns_server)
        if self.__dns_client > 0: self.delete_handler(self.__dns_client)
        if self.__dns_server6 > 0: self.delete_handler(self.__dns_server6)
        if self.__dns_client6 > 0: self.delete_handler(self.__dns_client6)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

    def auto_clean(self):
        now_t = time.time()

        # 设置每隔一段时间清理一次DNS映射记录
        if now_t - self.__up_dns_record_time < 5: return

        dels = []
        for _id in self.__id_wan2lan:
            t = self.__id_wan2lan[_id]["time"]
            if now_t - t < 5: continue
            dels.append(_id)

        for _id in dels:
            del self.__id_wan2lan[_id]

        self.__up_dns_record_time = now_t

    def add_ns_os_resolv(self):
        """加入nameserver到操作系统resolv中
        :return:
        """
        manage_addr = self.get_manage_addr()
        cls = os_resolv.resolv()
        # 如果存在那么不加入
        if cls.exists(manage_addr): return

        _list = cls.get_os_resolv()
        _list.insert(0, ("nameserver", manage_addr))
        # 修复操作系统DNS查询偶发性5秒延迟问题
        _list.insert(0, ("options", "single-request-reopen"))
        cls.write_to_file(_list)

    def update_pppoe_dns(self):
        now = time.time()
        if now - self.__read_pppoe_dns_time < 30: return

        ip4_nameservers = []

        nameservers = RPCClient.fn_call("router", "/config", "pppoe_dnsservers_get")
        for nameserver in nameservers:
            if not nameserver: continue
            ip4_nameservers.append(nameserver)

        if ip4_nameservers:
            ns1 = ip4_nameservers[0]
            if len(ip4_nameservers) >= 2:
                ns2 = ip4_nameservers[1]
                self.set_nameservers(ns1, ns2, is_ipv6=False)
            else:
                self.set_nameservers(ns1, "", is_ipv6=False)
            ''''''
        self.__read_pppoe_dns_time = now

    def myloop(self):
        now = time.time()

        self.auto_clean()
        if not self.__wan_ok:
            if now - self.__up_wan_ready_time < 10: return
            self.__wan_ok = RPCClient.fn_call("router", "/config", "wan_ready_ok")
            self.__up_wan_ready_time = now
            return

        if now - self.__up_autoset_icmpv6_dns_time > 60:
            self.auto_set_ipv6_dns()
            self.__up_autoset_icmpv6_dns_time = now

        # 一些Linux自带的软件在更新后会刷新/etc/resolv.conf文件
        # 因此这里需要定期检查改回来
        if now - self.__up_check_os_resolv_time > 60:
            self.add_ns_os_resolv()
            self.__up_check_os_resolv_time = now

        if self.is_pppoe_dial():
            self.update_pppoe_dns()

        self.__dns_cache.cache_loop()


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
