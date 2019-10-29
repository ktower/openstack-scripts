#!/bin/bash
#
# Script to live-migrate all instances on a compute node to another node
#
# Assume the environment is already configured to work with an OpenStack environment

WAITFLAG="--wait"
DOIT="yes"
SRCHOST=""
DESTHOST=""

function printusage()
{
    echo "n2n-migrate.sh [ --nowait ] [ --dry-run ] src_host dest_host"
}

# Process parameters
while [ $# -gt 2 ]; do
    case $1 in
        --nowait)
            WAITFLAG=""
            ;;
        --dry-run)
            DOIT="no"
            ;;
        *)
            printusage
            exit 1
    esac
    shift
done
if [ $# -eq 2 ]; then
    SRCHOST=$1
    DESTHOST=$2
else
    printusage
    exit 1
fi

echo "This script will live migrate all instances currently assigned to $SRCHOST to $DESTHOST."
instsondest=$(openstack server list --all-projects --host $DESTHOST -c Name -f value)
numinst=$(echo "${instsondest}" | wc -l)
if [ $numinst -gt 0 ]; then
   echo "WARNING: There are currently $numinst instances running on $DESTHOST:"
   echo "$instsondest"
   echo "Please ensure you have room on $DESTHOST to accept all of ${SRCHOST}'s workloads."
fi
echo "Do you wish to continue? (Y/n)"
read usercontinue

if [ "x$usercontinue" != "xY" ]; then
   exit 0
fi

for inst in $(openstack server list --all-projects --host $SRCHOST -c ID -f value); do
    openstack server show $inst | awk '/ name / {print $4}'
    if [ $DOIT == "yes" ]; then
       openstack server migrate --live $DESTHOST $WAITFLAG $inst
    else
       echo "Not executing: openstack server migrate --live $DESTHOST $WAITFLAG $inst"
    fi
done

exit 0