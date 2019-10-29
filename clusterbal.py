#!/usr/bin/env python3

import sys
import shade
import random
from prettytable import PrettyTable

# This script will produce a list of live migration commands to run in order to better balance
# an OpenStack cluster's workload evenly across all nodes.
# Notes:
# 1) The only metric used at this time is memory.
# 2) By default, all nodes in a cluster are used.  A future optimization would be to limit it
#    to only nodes in a specific AZ or aggregation group.  Specific nodes can be specified
#    on the command line, and the balancing algorithm will only consider those for source and
#    sink destinations.
# 3) At this time the script only provides advised actions.  No actual migrations will occur.

class osHypervisor:

    """A class that describes an OpenStack hypervisor and a list of all the instances running on it."""

    def __init__(self, name, totmem, curmem):
        self.__vmDict       = {}      # Stores a dictionary of VMs assigned to the hypervisor, indexed by ID
                                      # The element contains another dict with {name, ram, vcpus, disk}
        self.__name         = name    # The name of the hypervisor
        self.__hostTotalMB  = totmem  # How much memory, in MB, the host has
        self.__hostCurMemMB = curmem  # How much memory, in MB, the host is currently using
        self.__hostNewMemMB = curmem  # How much memory, in MB, the host will be using if plan is executed
    
    def getName(self):
        """Return the hypervisor name."""
        return self.__name
    def getNumInDict(self):
        """Return number of objects in __vmDict.  Mostly a debug function."""
        return len(self.__vmDict)
    def getCurPctFull(self):
        """Return a percentage of how full the hypervisor currently is."""
        return self.__hostCurMemMB / self.__hostTotalMB
    def getNewPctFull(self):
        """Return a percentage of how full the hypervisor will be if the plan is executed."""
        return self.__hostNewMemMB / self.__hostTotalMB
    def doesInstanceExist(self, id):
        """Returns True if we know about this instance, False if not."""
        if id in self.__vmDict:
            return True
        else:
            return False
    def addInstance(self, id, name="", ram=0, vcpus=0, disk=0, modifymemory=True):
        """Add an instance to the list of instances currently assigned to this hypervisor.
           If modifymemory=True, modify the hypervisor's memory usage."""
        if self.doesInstanceExist(id):
            print("WARNING: Instance {} already exist on {}. Data will be overwritten.".format(id, self.getName()))
        self.__vmDict[id] = { 'name': name, 'ram': ram, 'vcpus': vcpus, 'disk': disk }
        if modifymemory:
            self.__hostNewMemMB = self.__hostNewMemMB + ram  
    def rmInstance(self, id, modifymemory=True):
        """Remove an instance fromt he list of instances currently assigned to this hypervisor."""
        if not self.doesInstanceExist(id):
            print("WARNING: Instance {} to be removed from {} already does not exist.  Skipping.".format(id, self.getName()))
        else:
            if modifymemory:
                self.__hostNewMemMB = self.__hostNewMemMB - self.getInstRam(id)
            del self.__vmDict[id]
    def getRandInst(self):
        """Return a random instance ID from the list of existing instances on the server.
           Returns false if none exist."""
        if not self.__vmDict:
            print("WARNING: There are currently no instances assigned to {}".format(self.getName()))
            return False
        return random.choice(list(self.__vmDict.keys()))
    def getInstRam(self, id):
        """Given instance defined with id, return the amount of memory allocated to it.  If instance doesn't exist, return 0."""
        if not self.doesInstanceExist(id):
            return 0
        else:
            return self.__vmDict[id]['ram']

class flavorCache:
    """Shade libs won't let you enumerate all flavors in a cloud, so we'll look them up and 
       add them here as a cache as we find them."""
    __flavors = {}  # A dict of dicts, each element has {name, ram, vcpus, disk, ephemeral }

    def listFlavorsById(self):
        """Return a list of flavor UUIDs that we know about."""
        return list(self.__flavors.keys())
    def listFlavorsByName(self):
        """Return a list of flavors names that we know about."""
        flist = []
        for flavid in self.__flavors: 
            flist.append(self.__flavors[flavid]['name'])
        return flist
    def flavorExists(self,flav):
        """Returns True if flavor exits, False if not."""
        if flav in self.__flavors:
            return True
        else:
            return False
    def getFlavorResource(self, flav, rtype):
        """Returns the resource limit 'rtype' defined in flavor 'flav.'  If either flav or rtype
           don't exist, return False."""
        if not self.flavorExists(flav):
            return False
        if rtype not in self.__flavors[flav]:
            return False
        else:
            return self.__flavors[flav][rtype]
    def addFlavor(self, flavid, name="", ram=0, vcpus=0, disk=0, ephemeral=0):
        if self.flavorExists(flavid):
            print("WARNING: Flavor {} already exists in flavor cache.  It will be overwritten.".format(flavid))
        self.__flavors[flavid] = { 'name': name, 'ram': ram, 'vcpus': vcpus, 'disk': disk, 'ephemeral': ephemeral }

DEBUG=True      # Add extra messages?

def getHypervisors(cloud, hdict):
    """Get hypervisors and add them to hdict, a reference to a list of osHypervisor objects."""
    for host in cloud.list_hypervisors():
        hinfo = osHypervisor(host['hypervisor_hostname'], host['memory_mb'], host['memory_mb_used'])
        hdict[host['hypervisor_hostname']] = (hinfo)

def getFlavorInfo(cloud, fcache, flavor):
    """Given a flavor in cloud, return a tuple of data about it: [ram, vcpus, disk, ephemeral ].
       Also use the "Flavors" global cache object to reduce the number of API calls to make for
       flavors we already have looked up."""
    if not fcache.flavorExists(flavor):
        # Need to look up the flavor via the API instead.
        if DEBUG:
            print("Issuing API call to look up flavor {}".format(flavor))
        flavinfo = cloud.get_flavor(flavor)
        fname    = flavinfo['name']
        fram     = flavinfo['ram']
        fvcpus   = flavinfo['vcpus']
        fdisk    = flavinfo['disk']
        fephem   = flavinfo['ephemeral']
        fcache.addFlavor(flavor, name=fname, ram=fram, vcpus=fvcpus, disk=fdisk, ephemeral=fephem)
    
    return ( fcache.getFlavorResource(flavor, 'ram'),
             fcache.getFlavorResource(flavor, 'vcpus'),
             fcache.getFlavorResource(flavor, 'disk')
           )

def getFullestHyperMem(hdict):
    """Returns the (name, percentage) of the hypervisor with the most "current" in-use memory."""
    biggestname=None
    biggestpct=0.0
    for vm in hdict.keys():
        if hdict[vm].getNewPctFull() > biggestpct:
            biggestname=vm
            biggestpct=hdict[vm].getNewPctFull()
    return (biggestname, biggestpct)

def getEmptiestHyperMem(hdict):
    """Returns the (name, percentage) of the hypervisor with the least "current" in-use memory."""
    smallestname=None
    smallestpct=1.0
    for vm in hdict.keys():
        if hdict[vm].getNewPctFull() < smallestpct:
            smallestname=vm
            smallestpct=hdict[vm].getNewPctFull()
    return (smallestname, smallestpct)

def getPctDiff(pct1, pct2):
    """Given two percentages (float value 0 < n < 1), return the percent different between the two."""
    return abs(pct1 - pct2) / pct1

def getMigSummTable(hinfodict):
    """Returns a pretty table summarizing the hypervisors before and after."""
    htable = PrettyTable(['Node', 'Before', 'After', 'Final inst count'])
    htable.align['Before'] = 'r'
    htable.align['After'] = 'r'
    htable.align['Final inst count'] = 'r'
    for h in sorted(hinfodict.keys()):
        htable.add_row([hinfodict[h].getName(),
                          "{0:3.1f} %".format(hinfodict[h].getCurPctFull() * 100),
                          "{0:3.1f} %".format(hinfodict[h].getNewPctFull() * 100),
                          hinfodict[h].getNumInDict()]
                        )
    
    return htable

def main():
    """The main program here."""
    cloud          = shade.OpenStackCloud()  # Cloud connection object
    HypervisorDict = {} # Store osHyperVisor objects here
    PlanList       = [] # List of actions to take, in tuple form: (srchyper, desthyper, instance_id, memsize)
    Flavors        = flavorCache()  # A cache of flavor definitions
    tolerance      = 0.05  # How close in fullness percentage the hypervisors should be

    # Get basic information about our hypervisors, and store into global list "HypervisorList"
    try:
        getHypervisors(cloud, HypervisorDict)
    except:
        sys.exit("Unable to retrive list of cluster hypervisors.  Ensure you are connecting as a cloud admin and try again.")

    ## Populate VM data for each hypervisor
    for hyper in HypervisorDict.keys():
        hname = HypervisorDict[hyper].getName()
        slist=cloud.list_servers(all_projects=True, bare=True, filters={'host': hname})
        for s in slist:
            sid     = s['id']
            sname   = s['name']
            sflavor = s['flavor']['id']
            ( sram, svcpus, sdisk ) = getFlavorInfo(cloud, Flavors, sflavor)
            if DEBUG:
                print("Adding {} to {}'s instance list".format(sname, hname))
            # Don't modify hypervisor memory; we already have a total
            HypervisorDict[hyper].addInstance(sid, name=sname, ram=sram, vcpus=svcpus, disk=sdisk, modifymemory=False)

    
    ## Interatively pick random VM from most full hypervisor to move to least full
    ## Repeat until all hypervisors are within ~n percent of each other.
    (smallesthyper, smallestpct) = getEmptiestHyperMem(HypervisorDict)
    (biggesthyper, biggestpct) = getFullestHyperMem(HypervisorDict)
    while getPctDiff(biggestpct, smallestpct) > tolerance:
        if DEBUG:
            print("Hypervisor spread is {0:3.1f} percent, looking for VM to move from {1} to {2}...".format(getPctDiff(biggestpct,smallestpct) * 100, biggesthyper, smallesthyper))
        # Find an instance to move
        bighypercfg=HypervisorDict[biggesthyper]   # Is reference to osHypervisor object
        smallhypercfg=HypervisorDict[smallesthyper]

        vmtomove=bighypercfg.getRandInst()  # Is VM UUID
        vmtomovemem=bighypercfg.getInstRam(vmtomove)
        if DEBUG:
            print("Found {} ({} MB)".format(vmtomove, vmtomovemem))

        # Move instance from fullest to newest node
        # TODO: retain more than UUID and memory size.
        bighypercfg.rmInstance(vmtomove, modifymemory=True)
        smallhypercfg.addInstance(vmtomove, ram=vmtomovemem, modifymemory=True)

        # Record to plan for later output
        PlanList.append((biggesthyper, smallesthyper, vmtomove, vmtomovemem))

        # Update biggest/smallest and try again
        (smallesthyper, smallestpct) = getEmptiestHyperMem(HypervisorDict)
        (biggesthyper, biggestpct) = getFullestHyperMem(HypervisorDict)

    
    ## Output plan and quit
    print("### Plan calculated.  Output follows:")
    for mig in PlanList:
        # mig: (srchyper, desthyper, instance_id, memsize)
        print("# migrate {0} MB instance from {1} to {2}".format(mig[3], mig[0], mig[1]))
        print("openstack server migrate --live {0} --wait {1}".format(mig[1], mig[2]))

    print("### Plan Summary:")
    print("### Total migrations: {0}".format(len(PlanList)))
    print(getMigSummTable(HypervisorDict))


if __name__ == "__main__":
    main()
