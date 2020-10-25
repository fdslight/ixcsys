#define  PY_SSIZE_T_CLEAN

#include<Python.h>
#include<structmember.h>
#include<execinfo.h>
#include<signal.h>

typedef struct{
    PyObject_HEAD
}ip2socks;


