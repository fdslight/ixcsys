#!ipxe

menu Please choose Boot Type
item diskless   Diskless Boot
item installer  Install OS
item exit       Exit
choose --default exit --timeout 5000 target && goto ${target}
