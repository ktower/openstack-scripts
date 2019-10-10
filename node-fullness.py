#!/usr/bin/env python

import os_client_config, shade
from prettytable import PrettyTable

def main():
    """The Main Program"""
    cloud = shade.openstack_cloud()

    # Get all servers, across all projects
    #servers = cloud.list_servers(all_projects=True)

    # Get hypervisor info
    hyperlist = cloud.list_hypervisors()
    showHyperSum(hyperlist)

    
def showHyperSum(hlist):
    """Given a shade.list_hypervisors() output munch.Munch object, summarize hypervisor usage."""

    # Memory Consumption Table
    memTable = PrettyTable(['Node','Total Mem (GB)', 'Mem in-use (GB)', 'Mem Free (GB)', 'Mem % in-use'])
    memTable.align['Node'] = 'r'
    memTable.align['Total Mem (GB)'] = 'r'
    memTable.align['Mem in-use (GB)'] = 'r'
    memTable.align['Mem Free (GB)'] = 'r'
    memTable.align['Mem % in-use'] = 'r'
    memTable.float_format['Mem % in-use'] = '2.2'
    
    memTotals = [0,0,0]
    instCountTotal = 0

    # Instance Count Table
    instCountTable = PrettyTable(['Node', '# Instances'])
    instCountTable.align['Node'] = 'r'
    instCountTable.align['# Instances'] = 'r'

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

        instCountTable.add_row([host['hypervisor_hostname'],
                                host['running_vms'],
                               ])
        instCountTotal += host['running_vms']

    memTable.add_row(['--', '--', '--', '--', '--'])
    memTable.add_row(['TOTAL:'] + memTotals + [float(memTotals[1]) / float(memTotals[0]) * 100])

    instCountTable.add_row(['--', '--'])
    instCountTable.add_row(['TOTAL:'] + [instCountTotal])

    print "Memory Summary:"
    print memTable

    print "Instance Count:"
    print instCountTable

if __name__ == "__main__":
    main()
