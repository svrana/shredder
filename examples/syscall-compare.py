#!/usr/bin/env python

"""
Run this program:
    PYTHONPATH=. python example/syscall-compare.py

"""

from glob import glob
from subprocess import Popen, PIPE

ifconfig_by_iface = {}

for interface in glob('/sys/class/net/*'):
    name = interface.split('/')[-1]
    process = Popen(["ifconfig", name], stdout=PIPE)
    output, _ = process.communicate()
    process.wait()
    ifconfig_by_iface[name] = output

print "Found %d network interfaces: %s " % (len(ifconfig_by_iface.keys()),
                                            ifconfig_by_iface.keys())
print ifconfig_by_iface
