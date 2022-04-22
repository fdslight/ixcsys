#include<stdio.h>
#include<sys/time.h>


static inline
unsigned short calc_csum_a(unsigned short old_csum,unsigned short old_field,unsigned short new_field)
{
    unsigned long csum = old_csum - (~old_field & 0xFFFF) - new_field ;
    csum = (csum >> 16) + (csum & 0xffff);
    csum +=  (csum >> 16);
    return csum;
}

static inline
unsigned short calc_csum_b(unsigned short old_csum,unsigned short old_field,unsigned short new_field)
{
	__asm__ __volatile__(
		"notw %1;\n"
		"subw %1,%0;\n"
		"sbbw %2,%0;\n"
		"sbbw $0,%0;\n"
		:"=r"(old_csum)
		:"r"(old_field),"r"(new_field),"0"(old_csum)
	);

	return old_csum;
}



int main(int argc,char *argv[])
{

	struct timeval b,e;
	int count=10000;
	unsigned short v1,v2;

	gettimeofday(&b,NULL);
	for(int n=0;n<count;n++){
		v1=calc_csum_a(1200,2000,3000);
	}
	gettimeofday(&e,NULL);

	printf("CSUM_A:%d %d %d\r\n",v1,e.tv_sec-b.tv_sec,e.tv_usec-b.tv_usec);

	gettimeofday(&b,NULL);
	for(int n=0;n<count;n++){
		v2=calc_csum_b(1200,2000,3000);
	}
	gettimeofday(&e,NULL);
	printf("CSUM_B:%d %d %d\r\n",v2,e.tv_sec-b.tv_sec,e.tv_usec-b.tv_usec);


	return 0;
}
