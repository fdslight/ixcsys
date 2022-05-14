#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include<sys/socket.h>
#include<string.h>
#include<structmember.h>

#include "../../../pywind/clib/netutils.h"

static PyObject *
__is_same_subnet(PyObject *self,PyObject *args)
{
    unsigned char *address,*subnet;
    unsigned char prefix;
    int is_ipv6;
    Py_ssize_t sa,sb;

    if(!PyArg_ParseTuple(args,"y#y#Bp",&address,&sa,&subnet,&sb,&prefix,&is_ipv6)) return NULL;

    return PyBool_FromLong(is_same_subnet(address,subnet,prefix,is_ipv6));
}

static PyObject *
__is_same_subnet_with_msk(PyObject *self,PyObject *args)
{
    unsigned char *address,*subnet,*mask;
    int is_ipv6;
    Py_ssize_t sa,sb,sc;

    if(!PyArg_ParseTuple(args,"y#y#y#p",&address,&sa,&subnet,&sb,&mask,&sc,&is_ipv6)) return NULL;

    return PyBool_FromLong(is_same_subnet_with_msk(address,subnet,mask,is_ipv6));
}

static PyMethodDef racs_methods[] = {
	{"is_same_subnet",__is_same_subnet,METH_VARARGS,"is same subnet"},
    {"is_same_subnet_with_msk",__is_same_subnet_with_msk,METH_VARARGS,"is same subnet with mask"},

	{NULL,NULL,0,NULL}
};

static struct PyModuleDef racs_module = {
	PyModuleDef_HEAD_INIT,
	"racs_cext",
	NULL,
	-1,
	racs_methods
};


PyMODINIT_FUNC
PyInit_racs_cext(void)
{
	PyObject *m;

	m = PyModule_Create(&racs_module);

	if (NULL == m) return NULL;

	return m;

}