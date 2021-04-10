#!/usr/bin/env python3
import socket, struct, time, pickle, os

import pywind.lib.netutils as netutils

import ixc_syscore.DHCP.pylib.dhcp as dhcp
import ixc_syscore.DHCP.pylib.ipalloc as ipalloc


class dhcp_server(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None
    __client_hwaddr = None

    __alloc = None

    __TIMEOUT = 7200

    __mask_bytes = None
    __route_bytes = None
    __dns_bytes = None

    __dhcp_options = None

    __tmp_alloc_addrs = None
    __tmp_alloc_addrs_reverse = None

    __boot_file = None

    __addr_begin = None
    __addr_finish = None

    __ip_binds = None

    def __init__(self, runtime, my_ipaddr: str, hostname: str, hwaddr: str, addr_begin: str, addr_finish: str,
                 subnet: str, prefix: int):
        self.__runtime = runtime
        self.__dhcp_options = {}
        self.__tmp_alloc_addrs = {}
        self.__tmp_alloc_addrs_reverse = {}
        self.__ip_binds = {}

        self.__mask_bytes = socket.inet_pton(socket.AF_INET, netutils.ip_prefix_convert(prefix))
        self.__route_bytes = socket.inet_pton(socket.AF_INET, my_ipaddr)
        self.__dns_bytes = socket.inet_pton(socket.AF_INET, self.__runtime.manage_addr)

        self.__alloc = ipalloc.alloc(addr_begin, addr_finish, subnet, int(prefix))
        self.__my_ipaddr = socket.inet_pton(socket.AF_INET, my_ipaddr)
        self.__hostname = hostname
        self.__hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        self.__boot_file = runtime.server_configs["public"]["boot_file"]

        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()

        self.__addr_begin = addr_begin
        self.__addr_finish = addr_finish

        self.load_dhcp_cache()

    def get_dhcp_opt_value(self, options: list, code: int):
        rs = None
        for name, length, value in options:
            if name == code:
                rs = value
                break
            ''''''
        return rs

    def build_dhcp_response(self, msg_type: int, opts: list):
        brd_ifaddr = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])

        self.__dhcp_builder.op = 2
        self.__dhcp_builder.xid = self.__dhcp_parser.xid
        self.__dhcp_builder.secs = self.__dhcp_parser.secs
        self.__dhcp_builder.flags = self.__dhcp_parser.flags

        s_hwaddr = netutils.byte_hwaddr_to_str(self.__client_hwaddr)
        s_yiaddr = self.__alloc.get_ipaddr(s_hwaddr)
        if not s_yiaddr: return

        self.__dhcp_builder.chaddr = self.__client_hwaddr
        self.__dhcp_builder.ciaddr = socket.inet_pton(socket.AF_INET, s_yiaddr)

        src_hwaddr = self.__hwaddr
        if self.__dhcp_parser.flags:
            dst_hwaddr = brd_ifaddr
        else:
            dst_hwaddr = self.__client_hwaddr

        opts.insert(0, (53, struct.pack("B", msg_type)))
        opts.append((54, self.__my_ipaddr))

        link_data = self.__dhcp_builder.build_to_link_data(
            dst_hwaddr, src_hwaddr, bytes([0xff, 0xff, 0xff, 0xff]), self.__my_ipaddr,
            options=opts, is_server=True
        )
        self.__runtime.send_dhcp_server_msg(link_data)

    def get_resp_opts_from_request_list(self, request_list: bytes):
        """通过请求列表获取响应的options
        """
        resp_opts = []
        for code in request_list:
            if code == 1:
                resp_opts.append((code, self.__mask_bytes,))
            if code == 6 and self.__dns_bytes:
                resp_opts.append((code, self.__dns_bytes))
            # if code == 54:
            #    resp_opts.append((code, self.__my_ipaddr))
            if code == 3:
                resp_opts.append((code, self.__my_ipaddr))
            if code in self.__dhcp_options:
                resp_opts.append((code, self.__dhcp_options[code]))
            ''''''

        resp_opts.append((54, self.__my_ipaddr))
        resp_opts.append((51, struct.pack("!I", self.__TIMEOUT)))
        resp_opts.append((58, struct.pack("!I", int(self.__TIMEOUT * 0.5))))
        resp_opts.append((59, struct.pack("!I", int(self.__TIMEOUT * 0.8))))

        return resp_opts

    def handle_dhcp_discover_req(self, opts: list):
        request_list = self.get_dhcp_opt_value(opts, 55)
        if not request_list: return
        resp_opts = []
        s_client_hwaddr = netutils.byte_hwaddr_to_str(self.__client_hwaddr)

        ipaddr = self.__alloc.get_ipaddr(s_client_hwaddr)

        if not ipaddr: return
        if self.debug: print("DHCP ALLOC: %s for %s" % (ipaddr, s_client_hwaddr,))

        client_id = self.get_dhcp_opt_value(opts, 61)

        your_byte_ipaddr = socket.inet_pton(socket.AF_INET, ipaddr)
        self.__dhcp_builder.yiaddr = your_byte_ipaddr

        resp_opts.append((53, bytes([2])))
        if client_id:
            resp_opts.append((61, client_id))

        resp_opts += self.get_resp_opts_from_request_list(request_list)
        # 这里默认地址设置为不冲突,需要发送ARP检测
        self.__tmp_alloc_addrs[s_client_hwaddr] = {"time": time.time(), "ip": ipaddr, "neg_ok": False,
                                                   "conflict_check_ok": True}
        self.__tmp_alloc_addrs_reverse[ipaddr] = s_client_hwaddr

        self.__runtime.send_arp_request(self.__hwaddr, self.__my_ipaddr, dst_addr=your_byte_ipaddr, is_server=True)

        self.__dhcp_builder.flags = self.__dhcp_parser.flags
        self.__dhcp_builder.set_boot(self.__hostname, self.__boot_file)
        self.dhcp_msg_send(resp_opts)

    def dhcp_msg_send(self, resp_opts: list):
        flags = self.__dhcp_parser.flags & 0x8000
        if flags > 0:
            dst_hwaddr = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        else:
            dst_hwaddr = self.__client_hwaddr

        self.__dhcp_builder.xid = self.__dhcp_parser.xid
        self.__dhcp_builder.op = 2
        self.__dhcp_builder.siaddr = self.__my_ipaddr
        self.__dhcp_builder.chaddr = self.__client_hwaddr

        resp_data = self.__dhcp_builder.build_to_link_data(
            dst_hwaddr, self.__hwaddr, bytes([0xff, 0xff, 0xff, 0xff]), self.__my_ipaddr, resp_opts, is_server=True
        )
        self.__runtime.send_dhcp_server_msg(resp_data)

    def handle_dhcp_request(self, opts: list):
        s_client_hwaddr = netutils.byte_hwaddr_to_str(self.__client_hwaddr)
        now = time.time()

        # 如果不存在那么发送NAK直接告诉客户端重新发现
        if s_client_hwaddr not in self.__tmp_alloc_addrs:
            resp_opts = [(53, bytes([6]))]
            self.dhcp_msg_send(resp_opts)
            return
        o = self.__tmp_alloc_addrs[s_client_hwaddr]
        if now - o["time"] < 5 or not o["conflict_check_ok"]: return

        client_id = self.get_dhcp_opt_value(opts, 61)
        request_ip = self.get_dhcp_opt_value(opts, 50)
        # server_id = self.get_dhcp_opt_value(opts, 54)
        request_list = self.get_dhcp_opt_value(opts, 55)

        if not request_list: request_list = b""
        resp_opts = []

        if not request_ip or not client_id: return
        # 检查是否是本机器的DHCP请求
        # if server_id != self.__my_ipaddr: return

        resp_opts.append((53, bytes([5])))
        resp_opts += self.get_resp_opts_from_request_list(request_list)

        self.__dhcp_builder.yiaddr = request_ip

        # 设置DHCP协商成功
        o["neg_ok"] = True
        # 更新时间
        o["time"] = time.time()

        self.__alloc.bind_ipaddr(s_client_hwaddr, o["ip"])
        self.__dhcp_builder.set_boot(self.__hostname, self.__boot_file)

        self.dhcp_msg_send(resp_opts)

    def handle_dhcp_decline(self, opts: list):
        s_client_hwaddr = netutils.byte_hwaddr_to_str(self.__client_hwaddr)
        # 如果不存在那么直接DHCP请求
        request_ip = self.get_dhcp_opt_value(opts, 50)
        if not request_ip: return

        if s_client_hwaddr not in self.__tmp_alloc_addrs: return
        ip_addr = self.__tmp_alloc_addrs[s_client_hwaddr]["ip"]

        del self.__tmp_alloc_addrs[s_client_hwaddr]
        del self.__tmp_alloc_addrs_reverse[ip_addr]

        self.__alloc.unbind_ipaddr(s_client_hwaddr)

    def handle_dhcp_release(self, opts: list):
        s_client_hwaddr = netutils.byte_hwaddr_to_str(self.__client_hwaddr)
        # 如果不存在那么直接DHCP请求
        if s_client_hwaddr not in self.__tmp_alloc_addrs: return

        client_id = self.get_dhcp_opt_value(opts, 61)
        request_ip = self.get_dhcp_opt_value(opts, 50)
        server_id = self.get_dhcp_opt_value(opts, 54)

        if not request_ip or not client_id or not server_id: return

        if s_client_hwaddr not in self.__ip_binds:
            self.__alloc.unbind_ipaddr(s_client_hwaddr)
        ip_addr = self.__tmp_alloc_addrs[s_client_hwaddr]["ip"]

        del self.__tmp_alloc_addrs[s_client_hwaddr]
        del self.__tmp_alloc_addrs_reverse[ip_addr]

    def handle_dhcp_msg(self, msg: bytes):
        try:
            dst_hwaddr, src_hwaddr, dst_addr, src_addr, options, is_server = self.__dhcp_parser.parse_from_link_data(
                msg)
        except:
            return
        self.__dhcp_builder.reset()

        self.__client_hwaddr = src_hwaddr
        if not is_server: return
        x = self.get_dhcp_opt_value(options, 53)
        msg_type = x[0]
        if not msg_type: return

        if msg_type not in (1, 3, 4, 7,): return

        if msg_type == 1:
            self.handle_dhcp_discover_req(options)
            return

        if msg_type == 3:
            self.handle_dhcp_request(options)
            return

        if msg_type == 4:
            self.handle_dhcp_decline(options)
            return

        self.handle_dhcp_release(options)

    def handle_arp(self, dst_hwaddr: bytes, src_hwaddr: bytes, arp_info):
        # 只允许广播和发送到本机器的ARP数据包
        brd = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        if dst_hwaddr != brd or dst_hwaddr != self.__hwaddr: return
        op, _dst_hwaddr, _src_hwaddr, src_ipaddr, dst_ipaddr = arp_info
        if op != 2: return
        s_ip = socket.inet_ntop(socket.AF_INET, src_ipaddr)
        # 如果IP地址冲突那么删除分配
        conflict = True
        hwaddr = None

        if s_ip in self.__tmp_alloc_addrs_reverse:
            hwaddr = self.__tmp_alloc_addrs_reverse[s_ip]

        if conflict:
            del self.__tmp_alloc_addrs[hwaddr]
            del self.__tmp_alloc_addrs_reverse[s_ip]

    def set_timeout(self, timeout: int):
        """设置DHCP IP超时时间
        """
        self.__TIMEOUT = timeout

    @property
    def debug(self):
        return self.__runtime.debug

    def save_dhcp_cache(self):
        """保存DHCP保存,尽量避免地址错乱
        """
        path = "%s/dhcp_server.cache" % self.__runtime.conf_dir
        cache = {
            "my_ipaddr": self.__my_ipaddr,
            "addr_begin": self.__addr_begin,
            "addr_finish": self.__addr_finish,
            "bind": self.__alloc.bind
        }

        byte_data = pickle.dumps(cache)
        with open(path, "wb") as f: f.write(byte_data)
        f.close()

    def load_dhcp_cache(self):
        """加载DHCP缓存
        """
        path = "%s/dhcp_server.cache" % self.__runtime.conf_dir
        if not os.path.isfile(path): return

        with open(path, "rb") as f:
            byte_data = f.read()
        f.close()

        try:
            cache = pickle.loads(byte_data)
        except:
            return
        if not isinstance(cache, dict): return

        # 检查是否发生改变
        is_changed = False
        try:
            my_ipaddr = cache["my_ipaddr"]
            addr_begin = cache["addr_begin"]
            addr_finish = cache["addr_finish"]
            bind = cache["bind"]
        except KeyError:
            return

        if my_ipaddr != self.__my_ipaddr:
            is_changed = True

        if addr_begin != self.__addr_begin:
            is_changed = True
        if addr_finish != self.__addr_finish:
            is_changed = True
        if is_changed: return

        ip_bind = self.__runtime.dhcp_ip_bind
        binds = {}
        for name in ip_bind:
            info = ip_bind[name]
            hwaddr = info["hwaddr"]
            address = info["address"]
            binds[hwaddr] = address

        for hwaddr in bind:
            if hwaddr not in binds:
                self.__tmp_alloc_addrs[hwaddr] = {"time": time.time(), "ip": bind[hwaddr],
                                                  "neg_ok": False}
                self.__tmp_alloc_addrs_reverse[bind[hwaddr]] = hwaddr
            self.__alloc.bind_ipaddr(hwaddr, bind[hwaddr])
        self.__ip_binds = binds

    def loop(self):
        t = time.time()
        dels = []

        for hwaddr in self.__tmp_alloc_addrs:
            o = self.__tmp_alloc_addrs[hwaddr]
            old_t = o["time"]
            neg_ok = o["neg_ok"]
            # 大于1s那么就回收地址
            deleted = False
            if t - old_t > 10 and not neg_ok:
                deleted = True
                self.__alloc.unbind_ipaddr(hwaddr)
            if neg_ok and t - old_t >= self.__TIMEOUT:
                deleted = True
                self.__alloc.unbind_ipaddr(hwaddr)
            if deleted: dels.append(hwaddr)
            if deleted and self.debug: print("DHCP Free:%s for %s" % (o["ip"], hwaddr))
        for hwaddr in dels:
            ip = self.__tmp_alloc_addrs[hwaddr]["ip"]
            del self.__tmp_alloc_addrs[hwaddr]
            del self.__tmp_alloc_addrs_reverse[ip]
