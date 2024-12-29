#include <fcntl.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <linux/if.h>
#include <linux/if_tun.h>
#include <errno.h>
#include <net/route.h>
#include <sys/ioctl.h>
#include<sys/socket.h>
#include<string.h>
#include<sys/ioctl.h>
#include<netinet/in.h>
#include<unistd.h>
#include<stdio.h>

int tap_create(const char *name)
{
    struct ifreq ifr;
	int fd, err;

	if ((fd = open("/dev/net/tun", O_RDWR)) < 0){
        printf("ERROR:cannot open /dev/net/tun\n");
		return -1;
	}

	memset(&ifr, 0, sizeof(ifr));
	ifr.ifr_flags |= IFF_TAP | IFF_NO_PI;

	if (*name != '\0'){
		strncpy(ifr.ifr_name, name, IFNAMSIZ-1);
		ifr.ifr_name[IFNAMSIZ-1]='\0';
	}else{
        printf("ERROR:cannot create tap device %s\n" ,name);
        return -1;
    }

	if ((err = ioctl(fd, TUNSETIFF, (void *)&ifr)) < 0){
		close(fd);
        printf("ERROR:ioctl tap device %s\n" ,name);
		return -1;
	}

	return fd;
}

void tap_close(int fd)
{
	close(fd);
}

int tap_up(const char *name)
{
	int s;
	struct ifreq ifr;
	short flag;

	if ((s = socket(PF_INET, SOCK_STREAM, 0)) < 0) return -1;
	
	strcpy(ifr.ifr_name, name);

	flag = IFF_UP;
	if (ioctl(s, SIOCGIFFLAGS, &ifr) < 0) return -1;
	ifr.ifr_ifru.ifru_flags |= flag;

	if (ioctl(s, SIOCSIFFLAGS, &ifr) < 0) return -1;
	return 0;
}

int tap_set_nonblocking(int fd)
{
	int flags;

    flags=fcntl(fd,F_GETFL,0);
    return fcntl(fd,F_SETFL,flags | O_NONBLOCK);
}

ssize_t tap_read(int fd,void *buf,size_t buf_size)
{
    return read(fd,buf,buf_size);
}

ssize_t tap_write(int fd,void *buf,size_t buf_size)
{
    return write(fd,buf,buf_size);
}

