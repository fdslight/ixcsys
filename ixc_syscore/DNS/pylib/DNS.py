#!/usr/bin/env python3
import struct

DNS_HEADER_FMT = "!HHHHHH"


def drop_aaaa_request(dns_packet: bytes):
    """丢弃DNS AAAA请求
    """
    xid, flags, questions, anwser_rrs, authority_rrs, add_rrs = struct.unpack(DNS_HEADER_FMT, dns_packet[0:12])
    query_packet = dns_packet[12:]

    query_list = []
    result_list = []
    while 1:
        if not query_packet: break
        if questions == 0: break

        size = query_packet[0]
        query_list.append(struct.pack("!B", size))

        try:
            if size == 0:
                query_packet = query_packet[1:]
                query_type, = struct.unpack("!H", query_packet[0:2])
                query_class, = struct.unpack("!H", query_packet[2:4])

                query_list.append(query_packet[0:4])

                query_packet = query_packet[4:]

                if query_type != 28:
                    result_list += query_list
                else:
                    questions -= 1
                query_list = []
                continue

            e = size + 1
            tmp_data = query_packet[1:e]
            query_list.append(tmp_data)
            query_packet = query_packet[e:]
        except IndexError:
            return b""
        except struct.error:
            return b""
        ''''''
    # 如果没有问题那么丢弃数据包
    if questions == 0: return b""
    header = struct.pack(DNS_HEADER_FMT, xid, flags, questions, anwser_rrs, authority_rrs, add_rrs)
    # 这里需要把除questions之外的数据包添加回去
    return header + b"".join(result_list) + query_packet

# request_data = b"\x00\x94\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x0f\x73\x65\x61\x72\x63\x68\x72\x65\x63\x6f\x6d\x6d\x65\x6e\x64\x05\x6b\x75\x67\x6f\x75\x03\x63\x6f\x6d\x00\x00\x1c\x00\x01"
# print(request_data)
# print(drop_aaaa_request(request_data))
