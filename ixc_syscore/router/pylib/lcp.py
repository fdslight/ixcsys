#!/usr/bin/env python3
import os
import struct, random, time
import ixc_syslib.pylib.logging as logging

CFG_REQ = 1
CFG_ACK = 2
CFG_NAK = 3
CFG_REJECT = 4
TERM_REQ = 5
TERM_ACK = 6
CODE_REJECT = 7
PROTO_REJECT = 8
ECHO_REQ = 9
ECHO_REPLY = 10
DISCARD_REQ = 11

OPT_RESERVED = 0
OPT_MAX_RECV_UNIT = 1
OPT_AUTH_PROTO = 3
OPT_QUA_PROTO = 4
OPT_MAGIC_NUM = 5
OPT_PROTO_FIELD_COMP = 7
OPT_ADDR_CTL_COMP = 8

permit_opts = (
    OPT_MAX_RECV_UNIT, OPT_MAGIC_NUM, OPT_AUTH_PROTO,
)


class LCP(object):
    __pppoe = None
    __lcp_code_map_fn_set = None
    __my_magic_num = None
    __server_magic_num = None
    __my_id = 0

    __my_neg_status = None
    __server_neg_status = None
    __up_time = None

    __is_first = None

    def __init__(self, o):
        self.__pppoe = o
        self.__lcp_code_map_fn_set = {
            CFG_REQ: self.handle_cfg_req,
            CFG_ACK: self.handle_cfg_ack,
            CFG_NAK: self.handle_cfg_nak,
            CFG_REJECT: self.handle_cfg_reject,
            TERM_REQ: self.handle_term_req,
            TERM_ACK: self.handle_term_ack,
            CODE_REJECT: self.handle_code_reject,
            PROTO_REJECT: self.handle_proto_reject,
            ECHO_REQ: self.handle_echo_request,
            ECHO_REPLY: self.handle_echo_reply,
            DISCARD_REQ: self.handle_discard_req,
        }
        self.__up_time = time.time()

        self.reset()

    @property
    def debug(self):
        return self.__pppoe.debug

    def send(self, code: int, _id: int, byte_data: bytes):
        #if self.lcp_ok():
        #    self.__up_time = time.time()

        length = len(byte_data) + 4
        header = struct.pack("!BBH", code, _id, length)

        sent_data = b"".join([header, byte_data])
        self.__pppoe.send_data_to_ns(0xc021, sent_data)

    def send_echo_request(self):
        self.send(ECHO_REQ, self.__my_id, struct.pack("4s",os.urandom(4)))

    def send_cfg_req(self, options: list):
        _id = random.randint(1, 0xf0)
        seq = []
        for _type, value in options:
            seq.append(self.build_opt_value(_type, value))
        seq.append(self.build_opt_value(OPT_MAGIC_NUM, struct.pack("!I", self.__my_magic_num)))

        self.__my_id = _id
        byte_data = b"".join(seq)

        self.send(CFG_REQ, _id, byte_data)

    def build_opt_value(self, _type: int, opt_data: bytes):
        """构建LCP选项值
        """
        size = len(opt_data) + 2
        a = struct.pack("!BB", _type, size)

        return b"".join([a, opt_data])

    def check_auth_proto_fmt(self, byte_data: bytes):
        """检查验证协议是否有效
        """
        size = len(byte_data)
        if size < 2: return False

        proto, = struct.unpack("!H", byte_data[0:2])
        if proto not in (0xc023, 0xc223,): return False
        if proto == 0xc223 and size != 3: return False
        if proto == 0xc223 and byte_data[2] != 5: return False

        return True

    def get_auth_method(self, byte_data: bytes):
        proto = struct.unpack("!H", byte_data[0:2])
        if proto == 0xc223:
            return proto, byte_data[2]
        return proto, 0

    def parse_cfg_option(self, cfg_data: bytes):
        """解析配置选项
        """
        results = []
        tot_size = len(cfg_data)
        if tot_size < 2: return results
        idx = 0

        while 1:
            if idx == tot_size: break
            try:
                _type = cfg_data[idx]
                length = cfg_data[idx + 1]
            except IndexError:
                results = []
                if self.debug: print("Wrong LCP configure data")
                break

            if length < 2:
                results = []
                if self.debug: print("Wrong length field value for LCP")
                break

            length = length - 2
            idx += 2
            e = idx + length
            opt_data = cfg_data[idx:e]
            idx = e

            if len(opt_data) != length:
                results = []
                if self.debug: print("Wrong LCP option length field value")
                break
            if _type == OPT_MAGIC_NUM:
                try:
                    opt_data, = struct.unpack("!I", opt_data)
                except struct.error:
                    if self.debug: print("Wrong magic num data length")
                    results = []
                    break
                ''''''
            if _type == OPT_MAX_RECV_UNIT:
                try:
                    opt_data, = struct.unpack("!H", opt_data)
                except struct.error:
                    if self.debug: print("Wrong MRU data length")
                    results = []
                    break
                ''''''
            results.append((_type, opt_data,))
        return results

    def get_magic_num_from_opts(self, options: list):
        for _type, value in options:
            if _type == OPT_MAGIC_NUM: return value
        return None

    def handle_cfg_req(self, _id: int, byte_data: bytes):
        options = self.parse_cfg_option(byte_data)
        if not options: return
        magic_num = 0
        naks = []
        rejects = []
        acks = []
        is_error = False

        for _type, value in options:
            if _type not in permit_opts:
                rejects.append(self.build_opt_value(_type, value))
                continue
            if _type == OPT_MAX_RECV_UNIT:
                if value < 568 or value > 1492:
                    naks.append(self.build_opt_value(_type, struct.pack("!H", 1492)))
                    continue
                else:
                    self.__server_neg_status[OPT_MAX_RECV_UNIT]['value'] = value
                    self.__server_neg_status[OPT_MAX_RECV_UNIT]['neg_ok'] = True

                    acks.append(self.build_opt_value(_type, struct.pack("!H", value)))
                    continue
            if _type == OPT_MAGIC_NUM:
                magic_num = value
                continue
            if _type == OPT_AUTH_PROTO:
                if not self.check_auth_proto_fmt(value):
                    is_error = True
                    if self.debug: print("wrong auth protocol")
                    continue

                method, flags = self.get_auth_method(value)
                if method == 0xc023:
                    x = "pap"
                else:
                    x = "chap"
                self.__server_neg_status[OPT_AUTH_PROTO]['value'] = x
                self.__server_neg_status[OPT_AUTH_PROTO]['neg_ok'] = True
                acks.append(self.build_opt_value(_type, value))
            ''''''
        if is_error: return
        if magic_num <= 0: return
        self.__server_magic_num = magic_num

        if acks:
            acks.append(self.build_opt_value(OPT_MAGIC_NUM, struct.pack("!I", magic_num)))
            self.send(CFG_ACK, _id, b"".join(acks))
        if naks:
            naks.append(self.build_opt_value(OPT_MAGIC_NUM, struct.pack("!I", magic_num)))
            self.send(CFG_NAK, _id, b"".join(naks))
        if rejects:
            acks.append(self.build_opt_value(OPT_MAGIC_NUM, struct.pack("!I", magic_num)))
            self.send(CFG_REJECT, _id, b"".join(rejects))

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        self.__is_first = False

        options = self.parse_cfg_option(byte_data)
        if not options: return
        if _id != self.__my_id: return
        magic_num = self.get_magic_num_from_opts(options)
        if not magic_num: return
        if magic_num != self.__my_magic_num: return

        for _type, value in options:
            # 不在选项中说明服务器有问题
            if _type not in permit_opts:
                logging.print_error("pppoe server bug,reponse wrong option for ack")
                return
            if _type == OPT_MAGIC_NUM: continue
            if _type == OPT_MAX_RECV_UNIT:
                if value < 576 or value > 1492:
                    logging.print_error("pppoe server MRU size %d response wrong for ack" % value)
                    return
                else:
                    self.__my_neg_status[OPT_MAX_RECV_UNIT]['value'] = value
                    self.__my_neg_status[OPT_MAX_RECV_UNIT]['neg_ok'] = True
                    continue
            if _type == OPT_AUTH_PROTO:
                logging.print_error("pppoe server bug,the pppoe client LCP not send AUTH_PROTO option")
                return
            ''''''
        return

    def handle_cfg_nak(self, _id: int, byte_data: bytes):
        self.__is_first = False
        options = self.parse_cfg_option(byte_data)
        if not options: return
        if _id != self.__my_id: return
        # 如果magic num没有协商成功,那么丢弃数据包
        if self.__server_magic_num <= 0: return

        seq = []

        for _type, value in options:
            # 不在选项中说明服务器有问题
            if _type not in permit_opts:
                logging.print_error("pppoe server bug,reponse wrong option for nak")
                return
            if _type == OPT_MAGIC_NUM: continue
            if _type == OPT_MAX_RECV_UNIT:
                if value < 576 or value > 1492:
                    logging.print_error("pppoe server MRU size %d is not supported\r\n" % value)
                    return
                else:
                    seq.append((_type, struct.pack("!H", value),))
                    continue
            if _type == OPT_AUTH_PROTO:
                logging.print_error("pppoe server bug,the pppoe client LCP not send AUTH_PROTO option")
                return
            ''''''
        self.send_cfg_req(seq)

    def handle_cfg_reject(self, _id: int, byte_data: bytes):
        self.__pppoe.reset()
        logging.print_error("pppoe server bug,cannot support auth or MRU")

    def handle_term_req(self, _id: int, byte_data: bytes):
        self.send(TERM_ACK, _id, byte_data)
        self.__pppoe.reset()

    def handle_term_ack(self, _id: int, byte_data: bytes):
        pass

    def handle_code_reject(self, _id: int, byte_data: bytes):
        pass

    def handle_proto_reject(self, _id: int, byte_data: bytes):
        pass

    def handle_echo_request(self, _id: int, byte_data: bytes):
        self.send(ECHO_REPLY, _id, byte_data)

    def handle_echo_reply(self, _id: int, byte_data: bytes):
        self.__up_time = time.time()

    def handle_discard_req(self, _id: int, byte_data: bytes):
        pass

    def handle_packet(self, code: int, _id: int, byte_data: bytes):
        if code not in self.__lcp_code_map_fn_set:
            if self.debug: print("not found LCP code map value %d" % code)
            return

        self.__lcp_code_map_fn_set[code](_id, byte_data)

    def send_mru_neg_request(self):
        """发送MRU协商请求
        """
        o = self.__my_neg_status[OPT_MAX_RECV_UNIT]
        self.send_cfg_req([(OPT_MAX_RECV_UNIT, struct.pack("!H", o['value']))])

    def send_neg_request_first(self):
        """再服务器没响应的时候代表首次请求
        """
        options = []
        o = self.__my_neg_status[OPT_MAX_RECV_UNIT]
        options.append(
            (OPT_MAX_RECV_UNIT, struct.pack("!H", o['value']))
        )
        self.send_cfg_req(options)

    def start_lcp(self):
        self.send_neg_request_first()

    def lcp_ok(self):
        ok = True
        for code in self.__my_neg_status:
            if not self.__my_neg_status[code]['neg_ok']:
                ok = False
                break
            ''''''
        for code in self.__server_neg_status:
            if not self.__server_neg_status[code]["neg_ok"]:
                ok = False
                break
            ''''''
        return ok

    def loop(self):
        now = time.time()
        x = now - self.__up_time

        if self.__is_first:
            self.send_neg_request_first()
            return

        for opt_type in self.__my_neg_status:
            o = self.__my_neg_status[opt_type]
            neg_ok = o['neg_ok']
            if neg_ok: continue

            if opt_type == OPT_MAX_RECV_UNIT:
                self.send_mru_neg_request()
                return
            ''''''

        # 30s LCP未协商成功那么重新协商
        if x >= 30 and not self.lcp_ok():
            self.__pppoe.reset()
            return

        if self.lcp_ok():
            if x >= 60:
                self.send_echo_request()
                return
            # 大于90秒未回应那么重置PPPoE请求
            if x >= 90:
                self.__pppoe.reset()
                return

    def reset(self):
        magic_num = random.randint(1, 0xfffffff0)
        self.__my_magic_num = magic_num
        self.__server_magic_num = 0
        self.__my_id = 0
        self.__up_time = time.time()
        self.__is_first = True

        self.__my_neg_status = {
            OPT_MAX_RECV_UNIT: {"value": 1492, "neg_ok": False},
        }

        self.__server_neg_status = {
            OPT_MAX_RECV_UNIT: {"value": 1492, "neg_ok": False},
            OPT_AUTH_PROTO: {"value": "chap", "neg_ok": False}
        }

    def term_req(self):
        """终止请求
        """
        pass

    def auth_method_get(self):
        return self.__server_neg_status[OPT_AUTH_PROTO]['value']
