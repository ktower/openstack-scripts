#!/usr/bin/env python3

import shade
import random

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
TOLERANCE=0.10  # How close in fullness percentage the hypervisors should be

HypervisorDict = {} # Store osHyperVisor objects here
Flavors = flavorCache()

def getHypervisors(cloud):
    """Get hypervisors and add them to HypervisorList."""
    for host in cloud.list_hypervisors():
        hinfo = osHypervisor(host['hypervisor_hostname'], host['memory_mb'], host['memory_mb_used'])
        HypervisorDict[host['hypervisor_hostname']] = (hinfo)

def getFlavorInfo(cloud, flavor):
    """Given a flavor in cloud, return a tuple of data about it: [ram, vcpus, disk, ephemeral ].
       Also use the "Flavors" global cache object to reduce the number of API calls to make for
       flavors we already have looked up."""
    if not Flavors.flavorExists(flavor):
        # Need to look up the flavor via the API instead.
        if DEBUG:
            print("Issuing API call to look up flavor {}".format(flavor))
        flavinfo = cloud.get_flavor(flavor)
        fname    = flavinfo['name']
        fram     = flavinfo['ram']
        fvcpus   = flavinfo['vcpus']
        fdisk    = flavinfo['disk']
        fephem   = flavinfo['ephemeral']
        Flavors.addFlavor(flavor, name=fname, ram=fram, vcpus=fvcpus, disk=fdisk, ephemeral=fephem)
    
    return [ Flavors.getFlavorResource(flavor, 'ram'),
             Flavors.getFlavorResource(flavor, 'vcpus'),
             Flavors.getFlavorResource(flavor, 'disk')
            ]

def main():
    """The main program here."""
    cloud = shade.OpenStackCloud()

    # Get basic information about our hypervisors, and store into global list "HypervisorList"
    getHypervisors(cloud)

    ## Populate VM data for each hypervisor
    for hyper in HypervisorDict.keys():
        hname = HypervisorDict[hyper].getName()
        slist=cloud.list_servers(all_projects=True, bare=True, filters={'host': hname})
        for s in slist:
            sid     = s['id']
            sname   = s['name']
            sflavor = s['flavor']['id']
            [ sram, svcpus, sdisk ] = getFlavorInfo(cloud, sflavor)
            if DEBUG:
                print("Adding {} to {}'s instance list".format(sname, hname))
            # Don't modify hypervisor memory; we already have a total
            HypervisorDict[hyper].addInstance(sid, name=sname, ram=sram, vcpus=svcpus, disk=sdisk, modifymemory=False)

    
    ## TODO: Interatively pick random VM from most full hypervisor to move to least full
    ## TODO: Repeat until all hypervisors are within ~n percent of each other.
    ## TODO: Output plan and quit

if __name__ == "__main__":
    main()
