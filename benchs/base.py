import subprocess
import re
import sys
import csv
import os
import fileinput
from enum import Enum

# Global list of available benchmarks
base_benches = []

# Enum for device scheduler
class DeviceScheduler(Enum):
    NONE = 1
    MQ_DEADLINE = 2

# Generic class that a benchmark definition must implement.
class Bench(object):
    # output overwritten by setup()
    output = 'zbdbench_results'
    # container overwritten by setup()
    container = 'no'

    # Interface to be implemented by inheriting classes
    def id(self):
        return "Generic benchmark (name)"

    def setup(self, container, output):
        self.container = container
        self.output = output

    def run(self):
        print("Not implemented (run)")

    def teardown(self):
        print("Not implemented (teardown)")

    def report(self, path):
        print("Not implemented (report)")

    def plot(self, csv_file):
        print("Not implemented (plot)")

    def get_default_device_scheduler(self):
        return DeviceScheduler.MQ_DEADLINE

    # Helpers
    def result_path(self):
        if self.container == 'yes':
            return "/output"
        return self.output

    def container_sys_cmd(self, dev, extra_params):
        return f"podman run --device={dev}:{dev} -v \"{self.output}:/output\" --security-opt unmask=/sys/dev/block --security-opt seccomp=unconfined {extra_params}"

    def required_host_tools(self):
        return {'blkzone', 'blkdiscard'}

    def required_container_tools(self):
        return set()

    def sys_cmd(self, tool, dev, container, extra_container_params):
        exec_cmd = tool
        container_cmd = ''

        if container == 'yes':
            if tool == 'fio':
                exec_cmd = 'zfio'
            if tool == 'db_bench':
                exec_cmd = 'zrocksdb'
            if tool == 'zenfs':
                exec_cmd = '--entrypoint zenfs zrocksdb'
            if tool == 'mkfs.f2fs':
                exec_cmd = 'zf2fs'
            if tool == 'mkfs.xfs':
                exec_cmd = 'zxfs'

            container_cmd = self.container_sys_cmd(dev, extra_container_params)

        return f"{container_cmd} {exec_cmd}"

    def sys_container_dev(self, dev, container):
            return dev

    def get_dev_size(self, dev):
        devname = dev.strip('/dev/')

        with open('/sys/block/%s/size' % devname, 'r') as f:
            dev_size = int(f.readline())

        # Reported in 512B
        return (dev_size / 2)

    def get_number_of_max_open_zones(self, dev):
        devname = dev.strip('/dev/')
        nr_max_open_zones = 0
        with open(f"/sys/class/block/{devname}/queue/max_open_zones", 'r') as f:
            nr_max_open_zones = int(f.readline())
        return nr_max_open_zones

    def get_number_of_zones(self, dev):
        devname = dev.strip('/dev/')
        nr_zones = 0
        with open(f"/sys/class/block/{devname}/queue/nr_zones", 'r') as f:
            nr_zones = int(f.readline())
        return nr_zones

    def get_zone_size_mb(self, dev):
        devname = dev.strip('/dev/')
        zonesize = 0

        with open('/sys/block/%s/queue/chunk_sectors' % devname, 'r') as f:
            zonesize = int(((int(f.readline()) * 512) / 1024) / 1024)

        return zonesize

    def get_zone_capacity_mb(self, dev):
        devname = dev.strip('/dev/')

        with open(f'{self.output}/blkzone-report.txt', 'r') as f:
            capacity_blocks = int(f.readline().split()[5].strip(','), 0)
            capacity_bytes = capacity_blocks * 512
            capacity_mb = capacity_bytes / (1024**2)

        return capacity_mb

    def get_sector_size(self, dev):
        devname = dev.strip('/dev/')
        sectorsize = 0

        with open('/sys/block/%s/queue/logical_block_size' % devname, 'r') as f:
            sectorsize = int(f.readline())

        return sectorsize

    def get_nvme_drive_capacity_gb(self, path):
        filename = path + "/blkzone-capacity.txt"
        zoned_dev = os.path.exists(filename)
        if zoned_dev:
            with open(filename, 'r') as f:
                size_blocks = int(f.read().strip(), 0)
                size_bytes = size_blocks / 2
                size_gb = size_bytes / (1024 * 1024)
                return size_gb
        else:
            filename = path + "/lsblk-capacity.txt"
            lines = [l for l in fileinput.input(filename)]
            size_bytes = lines[1].split()[3]
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return size_gb

    def discard_dev(self, dev):
#        v = raw_input('Do you want to discard (y/N)?')
#        if v != 'y':
#            sys.exit(1)

        if is_dev_zoned(dev):
            subprocess.check_call("blkzone reset %s" % dev, shell=True)
        else:
            subprocess.check_call("blkdiscard %s" % dev, shell=True)

    def safe_csv_metadata(self, filename, content):
        with open(os.path.join(self.output, filename), 'w') as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(content)

    def run_cmd(self, dev, container, tool, tool_params, extra_container_params=''):
        cmd = "%s %s" % (self.sys_cmd(tool, dev, container, extra_container_params), tool_params)

        print("Exec: %s" % cmd)

#        v = raw_input('Do you want to execute: %s (y/N)?' % cmd)
#        if v != 'y':
#            sys.exit(1)

        subprocess.check_call(cmd, shell=True)
        return cmd

# Helper functions shared by scripts
def is_dev_zoned(dev):
    devname = dev.strip('/dev/')

    with open('/sys/block/%s/queue/zoned' % devname, 'r') as f:
        res = f.readline()

    return ("host-managed" in res)
