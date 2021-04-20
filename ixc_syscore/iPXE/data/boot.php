#!ipxe

menu Please choose Boot Type
item shell iPXE shell
item exit  Exit to BIOS

choose --default exit --timeout 5000 target && goto ${target}
exit

:shell
shell

:exit
exit