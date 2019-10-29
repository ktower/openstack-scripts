#!/bin/bash
if [ $# -lt 1 ]; then
   echo "Usage: $0 project_id_or_name"
   exit 1
fi

openstack quota set  \
   --cores 20 \
   --floating-ips 10 \
   --gigabytes 512 \
   --instances 10 \
   --networks 5 \
   --ram 40960 \
   --routers 2 \
   --snapshots 20 \
   --subnets 15 \
   --volumes 20 \
   $1
