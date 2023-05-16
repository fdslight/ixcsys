#!/usr/bin/env python3

import struct

FMT = "!BBHHH16s"
HEADER_SIZE = 24

MSG_TYPE_PING = 0
MSG_TYPE_PONG = 1
MSG_TYPE_AUTH = 2
MSG_TYPE_BRD_ADD = 3
MSG_TYPE_BRD_DEL = 4
MSG_TYPE_PUSH = 5
MSG_TYPE_PULL = 6

MSG_TYPES = (
    MSG_TYPE_PING,
    MSG_TYPE_PONG,
    MSG_TYPE_AUTH,
    MSG_TYPE_BRD_ADD,
    MSG_TYPE_BRD_DEL,
    MSG_TYPE_PUSH,
    MSG_TYPE_PULL,
)

ERR_NO = 0
# 未认证
ERR_NO_AUTH = 1
# 协议错误
ERR_NO_PROTO = 2
# 消息对象不存在
ERR_MSG_OBJ_NOT_EXISTS = 3
# 其他内部错误
ERR_INTERNAL = 4


class MSGProtoErr(Exception):
    pass


class builder(object):
    __session_id = None

    def __init__(self):
        self.__session_id = bytes(16)

    def __build_msg(self, _type, _id, msg_name: str, msg_content: bytes):
        if _type not in MSG_TYPES:
            raise MSGProtoErr("unkown msg type %d" % _type)

        byte_msg_name = msg_name.encode()

        msg_name_length = len(byte_msg_name)
        msg_content_length = len(msg_content)

        if msg_name_length > 0xfffe:
            raise MSGProtoErr("msg name is too long,max is 0xfffe")
        if msg_content_length > 0xffff:
            raise MSGProtoErr("msg content is too long,max is 0xfff0")

        header = struct.pack(FMT, 1, _type, _id, msg_name_length, msg_content_length, self.__session_id)

        return b"".join([header, msg_content])

    def __build_response_with_err_code(self, _type, _id, msg_name: str, msg_content: bytes, err_code=0):
        msg = struct.pack("!I", err_code) + msg_content

        return self.__build_msg(
            _type, _id, msg_name, msg
        )

    def set_session_id(self, session_id: bytes):
        self.__session_id = session_id

    def build_ping(self, _id):
        return self.__build_msg(
            MSG_TYPE_PING, _id, "", b""
        )

    def build_ping(self, _id):
        return self.__build_msg(
            MSG_TYPE_PONG, _id, "", b""
        )

    def build_auth_request(self, token: str):
        byte_auth_id = token.encode()
        if len(byte_auth_id) != 16:
            raise MSGProtoErr("wrong token value length")
        return self.__build_msg(
            MSG_TYPE_AUTH, 0, b"", byte_auth_id
        )

    def build_auth_response(self, msg: bytes, err_code=ERR_NO):
        return self.__build_response_with_err_code(
            MSG_TYPE_AUTH, 0, "", msg, err_code == err_code
        )
