#ifndef IXC_ISCSID_H
#define IXC_ISCSID_H


char *ixc_iscsid_run_dir_get(void);
void ixc_iscsid_set_as_no_listener(void);
int ixc_iscsid_is_debug(void);
void ixc_iscsid_set_pid_path(const char *path);
const char *ixc_iscsid_get_pid_path(void);

#endif