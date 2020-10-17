#!/usr/bin/env python

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


class LCP(object):
    __pppoe = None

    __lcp_code_map_fn_set = None

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

    @property
    def debug(self):
        return self.__pppoe.debug

    def parse_cfg_option(self, cfg_data: bytes):
        """解析配置选项
        """
        results = []
        if len(cfg_data) < 2: return results
        idx = 0
        while 1:
            try:
                _type = cfg_data[idx]
                length = cfg_data[idx + 1]
            except IndexError:
                results = []
                if self.debug: print("Wrong LCP configure data")
                break
            idx += 2
            e = idx + length
            opt_data = cfg_data[idx:e]
            if len(opt_data) != length:
                results = []
                if self.debug: print("Wrong LCP option length field value")
                break
            results.append((_type, opt_data,))
        return results

    def handle_cfg_req(self, _id: int, byte_data: bytes):
        options = self.parse_cfg_option(byte_data)
        if not options: return

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        options = self.parse_cfg_option(byte_data)
        if not options: return

    def handle_cfg_nak(self, _id: int, byte_data: bytes):
        options = self.parse_cfg_option(byte_data)
        if not options: return

    def handle_cfg_reject(self, _id: int, byte_data: bytes):
        options = self.parse_cfg_option(byte_data)
        if not options: return

    def handle_term_req(self, _id: int, byte_data: bytes):
        pass

    def handle_term_ack(self, _id: int, byte_data: bytes):
        pass

    def handle_code_reject(self, _id: int, byte_data: bytes):
        pass

    def handle_proto_reject(self, _id: int, byte_data: bytes):
        pass

    def handle_echo_request(self, _id: int, byte_data: bytes):
        pass

    def handle_echo_reply(self, _id: int, byte_data: bytes):
        pass

    def handle_discard_req(self, _id: int, byte_data: bytes):
        pass

    def handle_packet(self, code: int, _id: int, byte_data: bytes):
        if code not in self.__lcp_code_map_fn_set:
            if self.debug: print("not found LCP code map value %d" % code)
            return

        self.__lcp_code_map_fn_set[code](_id, byte_data)

    def start_lcp(self):
        pass

    def loop(self):
        pass
