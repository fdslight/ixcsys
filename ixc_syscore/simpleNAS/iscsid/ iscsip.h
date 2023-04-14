#ifndef IXC_ISCSIP_H
#define IXC_ISCSIP_H

struct ixc_iscsi_bhs{
    unsigned char opcode;
    unsigned char opcode_spec[3];
    unsigned char TotalAHSLength;
    unsigned char DataSegmentLength[3];
    unsigned char lun_or_opcode_spec[8];
    unsigned int InitiatorTaskTag[4];
    unsigned char opcode_spec2[28];
};

#endif