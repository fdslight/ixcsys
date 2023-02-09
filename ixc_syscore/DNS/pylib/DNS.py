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

#request_data=b"\x12\xd2\x44\xa4\xdd\xc0\x50\xeb\xf6\xe9\x7a\xaf\x08\x00\x45\x00\x00\x44\x40\xa2\x00\x00\x80\x11\x00\x00\xc0\xa8\x02\x64\xc0\xa8\x02\x02\xec\x08\x00\x35\x00\x30\x85\xf8\x38\x7c\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06\x63\x6c\x69\x65\x6e\x74\x03\x77\x6e\x73\x07\x77\x69\x6e\x64\x6f\x77\x73\x03\x63\x6f\x6d\x00\x00\x01\x00\x01"


#print(request_data)
#print(drop_aaaa_request(request_data))
