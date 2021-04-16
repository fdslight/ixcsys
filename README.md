# ixcsys
A software router for Linux

# dep envrionment
1. python3,python3 module dnspython3,cryptography and cloudflare-ddns


# debian/ubuntu install runtime
1. sudo apt install python3-pip
2. sudo pip3 install dnspython3
3. sudo pip3 install cryptography
4. sudo pip3 install cloudflare-ddns
5. sudo apt install libpython3-dev

# build ixcsys
1.first you need run "python3 build_config.py" for configure your environment(for debian 10 example,"python3 build_config.py --python3_include=/usr/include/python3.7m --python3_lib=/usr/lib/x86_64-linux-gnu")    
2.secondly you need run "python3 make.py build_all" for build all apps    
3.last run "python3 make.py install_all" for install to directory "/opt/ixcsys"    


# run ixcsys
1.first you must tell ixcsys your computer physical network card by run "python3 ixc_cfg.py" configure network card   
2.secondly run command "python3 ixc_main.py start" as root user   
3.last you can open "http://192.168.11.254" manage router by your browser  
4.the ixcsys default user is "admin" and password "admin"
