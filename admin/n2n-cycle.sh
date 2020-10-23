#!/bin/bash
#
# Script to live-migrate all instances on a compute node to another node and then return
# them to the original node.  This is used in cases where the underlying qemu binaries
# need to be restarted, but a restart of the instance is undesirable.
#
# Assume the environment is already configured to work with an OpenStack environment

WAITFLAG="--wait"
DOIT="yes"
SRCHOST=""
DESTHOST=""

function printusage()
{
    echo "$0 [ --nowait ] [ --dry-run ] src_host dest_host"
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

if [ $DOIT != "yes" ]; then
   echo "NOTE: Dry-run mode selected.  No migrations will occur."
fi
echo "This script will live migrate all instances currently assigned to $SRCHOST to $DESTHOST"
echo "one at a time and then migrate them back to $SRCHOST"
instsondest=$(openstack server list --all-projects --host $DESTHOST -c Name -f value)
numinst=$(echo "${instsondest}" | wc -l)
if [ $numinst -gt 0 ]; then
   echo "NOTE: There are currently $numinst instances running on $DESTHOST:"
   echo "$instsondest"
   echo "Please ensure you have room on $DESTHOST to accept the largest instance running on ${SRCHOST}."
fi
echo "Do you wish to continue? (Y/n)"
read usercontinue

if [ "x$usercontinue" != "xY" ]; then
   exit 0
fi

# For cycling purposes, we only want running instances
for inst in $(openstack server list --all-projects --host $SRCHOST --status ACTIVE -c ID -f value); do
    openstack server show $inst | awk '/ name / {print $4}'
    if [ $DOIT == "yes" ]; then
       openstack server migrate --live $DESTHOST $WAITFLAG $inst
       if [ $? -ne 0 ]; then
           echo "WARNING: Migration of $inst was unsuccessful (RC=$?).  Not attempting to migrate back to original host."
        else
           openstack server migrate --live $SRCHOST $WAITFLAG $inst
        fi
    else
       echo "Not executing: openstack server migrate --live $DESTHOST $WAITFLAG $inst"
       echo "Not executing: openstack server migrate --live $SRCHOST $WAITFLAG $inst"
    fi
    echo "########"
done

exit 0