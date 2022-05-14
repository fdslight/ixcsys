#!/usr/bin/env python3
"""
协议格式为
pad_length:1byte //加密的填充长度
user_id:16 bytes //用户key

"""
import sys, hashlib, struct

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("please install cryptography module")
    sys.exit(-1)


def _encrypt(key, iv, byte_data):
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    return encryptor.update(byte_data) + encryptor.finalize()


def _decrypt(key, iv, byte_data):
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    return decryptor.update(byte_data) + decryptor.finalize()


def get_size(byte_size):
    n = int(byte_size / 16)
    r = byte_size % 16

    if r != 0: n += 1

    return n * 16


def calc_str_md5(s: str):
    md5 = hashlib.md5()
    md5.update(s.encode())

    return md5.digest()


class crypto_base(object):
    __key = None

    def __init__(self):
        self.__key = None

    @property
    def key(self):
        return self.__key

    def set_key(self, key: str):
        key = calc_str_md5(key)
        self.__key = key


class encrypt(crypto_base):
    def wrap(self, user_id: bytes, byte_data: bytes):
        size = len(byte_data)
        new_size = get_size(size)
        x = new_size - size

        _list = [
            struct.pack("!B16s", x, user_id),
            _encrypt(self.key, user_id, b"".join([byte_data, b"\0" * x]))
        ]

        return b"".join(_list)


class decrypt(crypto_base):
    def unwrap(self, byte_data: bytes):
        if len(byte_data) < 17: return None

        pad_size = byte_data[0]
        user_id = byte_data[1:17]

        rs = _decrypt(self.key, user_id, byte_data[17:])
        size = len(rs) - pad_size

        return user_id, rs[0:size]


"""
import os
a=encrypt("hello")
b=decrypt("hello")

rs=a.wrap(os.urandom(16), b"hello,world,zzzzzzzzzzzzzzzzzzzzzzzzz")
print(b.unwrap(rs))
"""
