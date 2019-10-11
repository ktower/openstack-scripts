#!/usr/bin/env python3

import shade
from prettytable import PrettyTable

def getHyperSummTable(hlist):
    """Given a shade.list_hypervisors() output munch.Munch object, return a PrettyTable of hypervisor info."""

    hyperInfoTable = PrettyTable(['Node', 'Hyper Type', 'Hyper Version', 'State', 'Status'])
    for host in hlist:
        hyperInfoTable.add_row([host['hypervisor_hostname'],
                                host['hypervisor_type'],
                                host['hypervisor_version'], 
                                host['state'],
                                host['status'],
                                ])
    return hyperInfoTable

def getMemTable(hlist):
    """Given a shade.list_hypervisors() output munch.Munch object, return a PrettyTable of memory usage."""

    memTotals = [0,0,0]

    # Memory Consumption Table
    memTable = PrettyTable(['Node','Total Mem (GB)', 'Mem in-use (GB)', 'Mem Free (GB)', 'Mem % in-use'])
    memTable.align['Node'] = 'r'
    memTable.align['Total Mem (GB)'] = 'r'
    memTable.align['Mem in-use (GB)'] = 'r'
    memTable.align['Mem Free (GB)'] = 'r'
    memTable.align['Mem % in-use'] = 'r'
    memTable.float_format['Mem % in-use'] = '2.2'
    
    for host in hlist:
        memTable.add_row([host['hypervisor_hostname'], 
                          host['memory_mb'] / 1024, 
                          host['memory_mb_used'] / 1024,
                          host['free_ram_mb'] / 1024, 
                          float(host['memory_mb_used']) / float(host['memory_mb']) * 100,
                         ])
        memTotals[0] += host['memory_mb'] / 1024
        memTotals[1] += host['memory_mb_used'] / 1024
        memTotals[2] += host['free_ram_mb'] / 1024

    memTable.add_row(['--', '--', '--', '--', '--'])
    memTable.add_row(['TOTAL:'] + memTotals + [float(memTotals[1]) / float(memTotals[0]) * 100])

    return memTable
    
def getInstCountTable(hlist):
    """Given a shade.list_hypervisors() munch.Munch object, return a PrettyTable of instance counts."""
    instCountTotal = 0

    # Instance Count Table
    instCountTable = PrettyTable(['Node', '# Instances'])
    instCountTable.align['Node'] = 'r'
    instCountTable.align['# Instances'] = 'r'

    for host in hlist:
        instCountTable.add_row([host['hypervisor_hostname'],
                                host['running_vms'],
                               ])
        instCountTotal += host['running_vms']

    instCountTable.add_row(['--', '--'])
    instCountTable.add_row(['TOTAL:'] + [instCountTotal])

    return instCountTable

def getCPUTable(hlist):
    """Given a shade.list_hypervisors() munch.Munch object. return a PrettyTable of CPu usage."""
    cpuCount = 0
    cpuUsed  = 0

    cpuTable = PrettyTable(['Node', 'vCPUs', 'vCPUs Used', '% in use' ])
    cpuTable.align['Node'] = 'r'
    cpuTable.align['vCPUs'] = 'r'
    cpuTable.align['vCPUs Used'] = 'r'
    cpuTable.align['% in use'] = 'r'
    cpuTable.float_format['% in use'] = '2.2'

    for host in hlist:
        cpuTable.add_row([host['hypervisor_hostname'],
                          host['vcpus'],
                          host['vcpus_used'],
                          float(host['vcpus_used']) / float(host['vcpus']) * 100,
                          ])
        cpuCount += host['vcpus']
        cpuUsed += host['vcpus_used']
    
    cpuTable.add_row(['--', '--', '--', '--'])
    cpuTable.add_row(['TOTAL:',
                       cpuCount,
                       cpuUsed,
                       float(cpuUsed) / float(cpuCount) * 100,
                     ])
    
    return cpuTable

def showHyperSum(hlist):
    """Given a shade.list_hypervisors() output munch.Munch object, summarize hypervisor usage."""

    print("Hypervisor Summary:")
    print(getHyperSummTable(hlist))

    print("Memory Summary:")
    print(getMemTable(hlist))

    print("Instance Count:")
    print(getInstCountTable(hlist))

    print("CPU Usage Summary")
    print(getCPUTable(hlist))

def main():
    """The Main Program"""
    cloud = shade.openstack_cloud()

    # Get all servers, across all projects
    #servers = cloud.list_servers(all_projects=True)

    # Get hypervisor info
    hyperlist = cloud.list_hypervisors()
    showHyperSum(hyperlist)

if __name__ == "__main__":
    main()
