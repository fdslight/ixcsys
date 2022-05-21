#!/usr/bin/env python3
# 二进制安装器
import sys, os, hashlib

PKG_FILE = "{{PKG_FILE}}"


def check_file_hash(file_path):
    fdst = open(file_path, "rb")
    magic = fdst.read(7)

    if magic != b"ixcsys\n":
        print("ERROR:it is not ixcsys software package")
        return False
    md5_hash = hashlib.md5()
    md5_val = fdst.read(16)

    while 1:
        byte_data = fdst.read(8192)
        if not byte_data: break
        md5_hash.update(byte_data)

    fdst.close()

    if md5_val != md5_hash.digest():
        print("ERROR:wrong file hash value")
        return False

    return True


def main():
    if not os.path.isfile(PKG_FILE):
        print("ERROR:not found file %s" % sys.argv[1])
        return

    if not check_file_hash(PKG_FILE): return

    fdst = open(PKG_FILE, "rb")
    # 丢弃前面23个字节magic+md5
    fdst.read(23)
    new_file = "/tmp/ixcsys_temp.tar.gz"
    fdst_temp = open(new_file, "wb")

    while 1:
        read_data = fdst.read(8192)
        if not read_data: break
        fdst_temp.write(read_data)

    fdst.close()
    fdst_temp.close()

    os.system("tar xf %s -C /opt/ixcsys" % new_file)
    print("install ixcsys OK")


if __name__ == '__main__': main()
