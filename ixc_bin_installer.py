#!/usr/bin/env python3
# 二进制安装器
import sys, os, hashlib


def check_file_hash(md5_v, file_path):
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
    if len(sys.argv) != 2:
        print("ERROR:not found ixcsys binary file")
        return

    if not os.path.isfile(sys.argv[1]):
        print("ERROR:not found file %s" % sys.argv[1])
        return

    fdst = open(sys.argv[1], "rb")
    md5_hash = fdst.read(16)

    new_file = "/tmp/ixcsys_temp.tar.gz"
    fdst_temp = open(new_file, "wb")
    while 1:
        read_data = fdst.read(8192)
        if not read_data: break
        fdst_temp.write(read_data)

    fdst.close()
    fdst_temp.close()

    if not check_file_hash(md5_hash, new_file):
        print("ERROR:wrong file md5 value")
        os.remove(new_file)
        return

    os.system("tar xf %s -C /tmp/ixcsys_test" % new_file)
    print("install ixcsys OK")


if __name__ == '__main__': main()
