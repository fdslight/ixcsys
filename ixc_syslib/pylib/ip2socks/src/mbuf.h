#ifndef IP2SOCKS_MBUF_H
#define IP2SOCKS_MBUF_H

struct mbuf{
    struct mbuf *next;
#define MBUF_BEGIN 256
    int begin;
    int offset;
    int tail;
    int end; 
    unsigned char data[0xffff];
};

#endif