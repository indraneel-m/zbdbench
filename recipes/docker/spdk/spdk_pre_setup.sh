#!/usr/bin/bash
#spdk pre-launch setup script for containerised environment

cd /root/spdk_bin

param_str=$1

#Tokenise the cmdline arg for ' '
tokens=( $1)
device=${tokens[0]}

#Strip '/dev/' string out of '/dev/nvmeXnY' string
devname=$(sed 's/.*'dev'//' <<< $device)

#Now remove the '/dev/nvmeXnY' string from the orig cmdline arg
param_str=${param_str/$device/" "}

#Edit the json file and update /dev/nvmeXnY as per device sent by host
sed -i 's|\/nvme.*|'$devname'",|g' examples/bdev/fio_plugin/bdev_zoned_uring.json

#Kernel module required by SPDK
modprobe vfio-pci

#Reserve hugepages. PCI_ALLOWED="none" as we are not using SPDK nvme driver
PCI_ALLOWED="none" ./scripts/setup.sh

cd /

exec fio --filename=bdev_nvme $param_str

