def set_file(filename: str):
    byte_s = filename.encode("iso-8859-1")
    if len(filename) > 127:
        raise ValueError("wrong filename length")
    filled = bytes(128 - len(byte_s))
    file = b"".join([byte_s, filled])
    print(len(file))


set_file("128")