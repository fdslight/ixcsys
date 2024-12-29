必需环境:dotnet

1.ARM64 Linux运行build_arm64.sh构建,x86_64 Linux运行build_x64.sh构建
2.构建完毕后拷贝liblinux_tap.so到本目录"bin/Release/dotnet版本/对应架构/publish"目录下面
3.使用root启动PASSClient二进制程序
4.命令参数依次为"本地物理网卡名称 本地端口 远程主机地址 密钥"