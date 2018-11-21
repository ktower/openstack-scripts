#!/bin/bash

nova list | awk '{print $12"  "$4}' | sed 's/^boinc-network=//' | sed 's/,//'

