#!ipxe

dhcp
chain http://${next-server}/sysadm/diskless/boot?hwaddr=${mac}