# ixcsys
A software router for Linux   

# Hardware requirement
1. CPU:x86_64 with SSE2,arrch64 with NEON or other 64bit CPU.
2. Memory:1GB at least,2GB recommend.

# dep envrionment
1. python3,tftpd-hpa,curl,python3 module dnspython3,cryptography and cloudflare-ddns


# debian/ubuntu install runtime
1. sudo apt install python3-pip 
2. sudo pip3 install dnspython3 
3. sudo pip3 install cryptography 
4. sudo pip3 install cloudflare-ddns 
5. sudo pip3 install s-tui 
6. sudo apt install libpython3-dev  
7. sudo apt install tftpd-hpa 
8. sudo apt install pkg-config 
9. sudo apt install lsb-release 
10. sudo apt install curl 

# build ixcsys
1.first you need run "python3 configure.py" for configure your environment(for example,"python3 build_config.py nodebug")     
2.secondly you need run "python3 make.py build_all" for build all apps     
3.last run "python3 make.py install_all" for install to directory "/opt/ixcsys"    


# run ixcsys
1.first you must tell ixcsys your computer physical network card by run "python3 ixc_cfg.py" configure network card   
2.secondly run command "python3 ixc_main.py start" as root user   
3.last you can open "http://192.168.11.254 or http://router.ixcsys.com" manage router by your browser  
4.the ixcsys default user is "admin" and password "admin"

# software update
1. git pull origin master
2. python3 make.py build_all
3. python3 make.py gen_update
4. cd /opt/ixcsys
5. sudo python3 ixc_main.py restart
6. plan update: sudo python3 ixc_cron_updater hours:minutes

# about Packet forwarding speed(the software only support single-core forward packet)
1.Intel J1800 CPU or arm cortex-a53:100Mbit/s  
2.Intel N5105:1000Mbit/s     
3.Raspberry PI 4 or arm cortex-A72:300Mbit/s   
4.AMD Opteron x3421:500Mbit/s   

# why use Linux tuntap
netmap is not the part of Linux kernel,though FreeBSD support netmap,but FreeBSD less hardware is supported.