#!/bin/sh

cd ../ipxe-1.21.1/src

make -j8 bin/undionly.kpxe EMBED=../../ixcsys/ixc_syscore/sysadm/data/ipxe_embed.php CERT=../../ixcsys/shared_data/ca-bundle.crt TRUST=../../ixcsys/shared_data/ca-bundle.crt NO_WERROR=1
make -j8 bin-x86_64-efi/ipxe.efi EMBED=../../ixcsys/ixc_syscore/sysadm/data/ipxe_embed.php CERT=../../ixcsys/shared_data/ca-bundle.crt TRUST=../../ixcsys/shared_data/ca-bundle.crt NO_WERROR=1

cp bin-x86_64-efi/ipxe.efi ../../ixcsys/ixc_syscore/DHCP/data/ipxe.efi
cp bin/undionly.kpxe ../../ixcsys/ixc_syscore/DHCP/data/undionly.kpxe

cd ../../ixcsys