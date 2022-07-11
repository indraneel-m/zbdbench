import csv
import sys
from statistics import mean
from .base import base_benches, Bench, DeviceScheduler
from benchs.base import is_dev_zoned

class Run(Bench):
    jobname = "spdk_fio_zone_write"
    loops = 6

    def __init__(self):
        pass

    def get_default_device_scheduler(self):
        return DeviceScheduler.NONE

    def id(self):
        return self.jobname

    def setup(self, dev, container, output):
        super(Run, self).setup(output)

        self.discard_dev(dev)

    def required_container_tools(self):
        return super().required_container_tools() |  {'spdk-fio'}

    def run(self, dev, container, spdk_path):
        extra = ''
        max_open_zones = 14
        spdk_json_path = ''
        output_path_prefix = "output"
        devname = dev

        if spdk_path is not None:
            spdk_json_path = ("--spdk_json_conf=%s/examples/bdev/fio_plugin/bdev_zoned_uring.json") % spdk_path
            if container == 'yes':
                output_path_prefix = "/" + output_path_prefix
            else:
                output_path_prefix = self.output
                devname = "bdev_nvme"

        if is_dev_zoned(dev):
            # Zone Capacity (52% of zone size)
            zonecap=52
        else:
            # Zone Size = Zone Capacity on a conv. drive
            zonecap=100
            extra = '--zonesize=1102848k'

        io_size = int(((self.get_dev_size(dev) * zonecap) / 100) * self.loops)

        fio_param = ("--filename=%s"
                    " --io_size=%sk"
                    " --log_avg_msec=1000"
                    " --thread=1"
                    " --write_bw_log=%s/%s"
                    " --output=%s/%s.log"
                    " --ioengine=%s/build/fio/spdk_bdev --direct=1 --zonemode=zbd"
                    " --name=seqwriter --rw=randwrite"
                    " --bs=64k --max_open_zones=%s %s %s"
                    ) % (devname, io_size, output_path_prefix,  self.jobname, output_path_prefix, self.jobname, spdk_path, max_open_zones, extra, spdk_json_path)



        if container == 'yes':
            fio_param = '"' + fio_param + '"'

        self.run_cmd(dev, container, 'spdk-fio', fio_param)

    def teardown(self, dev, container):
        pass

    def report(self, dev, path):

        devcap = self.get_nvme_drive_capacity_gb(dev, path)
        if devcap is None:
            print("Could not get drive capacity for report")
            sys.exit(1)

        dp = []
        dy = []

        filename = (path + "/" + self.jobname + "_bw.1.log")
        with open(filename, 'r') as f:
            data = csv.reader(f, delimiter=',')
            for n in data:
                dy.append(int(n[1]) / 1024)

        ds = range(0, devcap)
        sum_max = sum(dy) / devcap

        spill = 0
        prev = 0
        for i in enumerate(ds):
            s = spill
            new_prev = prev
            while s < sum_max and new_prev < len(dy):
                s = s + dy[new_prev]
                if s < sum_max:
                    new_prev += 1
                else:
                    spill = s - sum_max

            dp.append(int(mean(dy[prev:new_prev])))
            prev = new_prev + 1

        dsx = [i * self.loops for i in ds]

        csv_file = path + "/" + self.jobname + ".csv"
        with open(csv_file, 'w') as csvfile:
            cw = csv.writer(csvfile, delimiter=',')
            cw.writerow(['written_gb', 'write_avg_mbs'])
            cw.writerows(list(map(list, zip(*[dsx, dp]))))

        print("  Output written to: %s" % csv_file)
        return csv_file

base_benches.append(Run())
