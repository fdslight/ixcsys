# ixcsys
A software router for Linux   

# CPU requirement
X86_64 with SSE2 or ARM64 with NEON

# dep envrionment
1. python3,tftpd-hpa,python3 module dnspython3,cryptography and cloudflare-ddns


# debian/ubuntu install runtime
1. sudo apt install python3-pip
2. sudo pip3 install dnspython3
3. sudo pip3 install cryptography
4. sudo pip3 install cloudflare-ddns
5. sudo apt install libpython3-dev  
6. sudo apt install tftpd-hpa
7. sudo apt install pkg-config
8. sudo apt install lsb-release

# build ixcsys
1.first you need run "python3 configure.py" for configure your environment(for example,"python3 build_config.py default")    
2.secondly you need run "python3 make.py build_all" for build all apps
3.last run "python3 make.py install_all" for install to directory "/opt/ixcsys"    


# run ixcsys
1.first you must tell ixcsys your computer physical network card by run "python3 ixc_cfg.py" configure network card   
2.secondly run command "python3 ixc_main.py start" as root user   
3.last you can open "http://192.168.11.254 or http://router.ixcsys.com" manage router by your browser  
4.the ixcsys default user is "admin" and password "admin"

# about Packet forwarding speed(the software only support single-core forward packet)
1.Intel J1800 CPU or arm cortex-a53:200Mbit/s  
2.Intel N5105:1000Mbit/s at least  
3.Raspberry PI 4 or arm cortex-A72:300Mbit/s  

# why use Linux tuntap
netmap is not the part of Linux kernel,though FreeBSD support netmap,but it is difficult for the most people.