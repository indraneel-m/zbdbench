# ZBDBench: Benchmark Suite for Zoned Block Devices

ZBDBench is a collection of benchmarks for zoned storage devices (Zoned Namespace (ZNS) SSDs and Shingled-Magnetic Recording (SMR) HDDs) that tests both the raw performance of the device, and runs standard benchmarks for applications such as RocksDB (dbbench) and MySQL (sysbench).

Community
---------
For help or questions about zbdbench usage (e.g. "how do I do X?") see [ZonedStorage.io](https://zonedstorage.io), our [Matrix](https://app.element.io/#/room/#zonedstorage-general:matrix.org) chat, or on [Slack](https://join.slack.com/t/zonedstorage/shared_invite/zt-uyfut5xe-nKajp9YRnEWqiD4X6RkTFw).


To report a bug, file a documentation issue, or submit a feature request, please open a GitHub issue.

For release announcements and other discussions, please subscribe to this repository or join us on Matrix.

Dependencies
------------

The benchmark tool requires Python 3.4+. In addition to a working python
environment, the script requires the following installed:

 - Linux kernel 5.9 or newer
   - Check your loaded kernel version using:
     `uname -a`

 - nvme-cli
   - Ubuntu: `sudo apt-get install nvme-cli`
   - Fedora: `sudo dnf -y install nvme-cli`

 - blkzone and blkdiscard (available through util-linux)
   - Ubuntu: `sudo apt-get install util-linux`
   - Fedora: `sudo dnf -y install util-linux-ng`
   - CentOS: `sudo yum -y install util-linux-ng`

 - a valid container (podman) environment
   - If you do not have a container environment installed, please see [this
     link](https://podman.io/getting-started/installation)

 - installed containers:
   - zfio - contains latest fio compiled with zone capacity support
   - zrocksdb - contains rocksdb with zenfs built-in
   - zzenfs - contains the zenfs tool to inspect the zenfs file-system

   The containers can be installed with:
     `cd recipes/docker; sudo ./build.sh`

   The container installation can be verified by listing the image:
     `sudo podman images`

  - matplotlib, pandas and openpyxl for graph plotting
    ```
    sudo pip install matplotlib
    sudo pip install pandas
    sudo pip install openpyxl
    ```

Getting Started
---------------

The run.py script runs a set of predefined benchmarks on a block device.

The block device does not have to be zoned - the workloads will work
on both types of block devices.

The script performs a set of checks before running the benchmarks, such as
validating that it is about to write to a block device, not mounted, and ready.

After all benchmarks have run, their output is availble in:

    zbdbench_results/YYYYMMDDHHMMSS (date format is replaced with the current time)

Each benchmark has a report function, which creates a csv file with the
specific output. See the section below for the csv format for each benchmark.

To execute all benchmarks, run:

    ./run.py -d /dev/nvmeXnY

If you have the latest fio installed, you may skip the container installation and
run the benchmarks using the system commands.

    ./run.py -d /dev/nvmeXnY -c no

To list available benchmarks, run:

    ./run.py -l

To only run a specific benchmark, append -b <benchmark_name> to the command:

    ./run.py -d /dev/nvmeXnY -b fio_zone_mixed

## WARNING

You need to have read/write permissions to the device or file you are
targeting. Usually block devices are owned by `root` user or `disk` group. You
can either change ownership of the block device your are testing:

    sudo chown myusername /dev/nvmeXnY

or make it world writable:

    sudo chmod o+rw /dev/nvmeXnY

Or elevate the privileges when running `zbdbench`:

    sudo ./run.py <args>

Please be sure that you are familiar with the security implications of the
option you choose. If you start a test on a different block device than the one
you intended, you may loose data and your system may fail to boot.

Command Options
---------------

List available benchmarks:

    ./run.py -l

Run specific benchmark:

    ./run.py -b benchmark -d /dev/nvmeXnY

Run fio_zone_xxx benchmarks with SPDK FIO plugin(io_uring zoned bdev) in a container env.:

    ./run.py -b fio_zone_xxx --mq-deadline-scheduler -d /dev/nvmeXnY -s yes -c yes

Run fio_zone_xxx benchmarks with SPDK FIO plugin(io_uring zoned bdev) directly on Host System.
Zbdbench will checkout and build SPDK(also FIO) in dir provided using --spdk-path option:

    ./run.py -b fio_zone_xxx --mq-deadline-scheduler -d /dev/nvmeXnY -s yes -c no --spdk-path /dir/path

Run all benchmarks:

    ./run.py -d /dev/nvmeXnY

Regenerate a report (and its plots)

    ./run.py -b fio_zone_mixed -r zbdbench_results/YYYYMMDDHHMMSS

Regenerate plots from existing csv report

    ./run.py -b fio_zone_throughput_avg_lat -p zbdbench_results/YYYYMMDDHHMMSS/fio_zone_throughput_avg_lat.csv

Overwrite benchmark run with the none device scheduler:

    ./run.py -b benchmark -d /dev/nvmeXnY --none-scheduler

Overwrite benchmark run with the mq-deadline device scheduler:

    ./run.py -b benchmark -d /dev/nvmeXnY --mq-deadline-scheduler

Benchmarks
----------

All fio benchmarks are setting the none scheduler by default if the iodepth is 1.

SPDK FIO plugin support:
  - Following benchmarks have SPDK FIO plugin support
     - fio_zone_write
     - fio_zone_mixed
     - fio_zone_throughput_avg_lat
  - Adding SPDK FIO plugin support for a new benchmark
     - See benchs/template.py for guidance

## fio_zone_write
  - executes a fio workload that writes sequential to 14 zones in parallel and
    while writing 6 times the capacity of the device.

  - generated csv output (fio_zone_write.csv)
    1. written_gb: gigabytes written (GB)
    2. write_avg_mbs: average throughput (MB/s)

## fio_zone_mixed
  - executes a fio workload that first preconditions the block device to steady
    state. Then rate limited writes are issued, in which 4KB random reads
    are issued in parallel. The average latency for the 4KB random read is
    reported.

  - generated csv output (fio_zone_mixed.csv)
    1. write_avg_mbs_target: target write throughput (MB/s)
    2. read_lat_avg_us: avg 4KB random read latency (us)
    3. write_avg_mbs: write throughput (MB/s)
    4. read_lat_us_avg_measured: avg 4KB random read latency (us)
    5. clat_*_us: Latency percentiles

    ** Note that (2) is only reported if write_avg_mbs_target and write_avg_mbs
       are equal. When they are not equal, the reported average latency is
       misleading, as the write throughput requested has not been possible to
       achieve.

## fio_zone_throughput_avg_lat
  - Executes all combinations of the following workloads report the throughput
    and latency in the csv report (Note: 14 is a possible value for max_open_zones):
      - Sequential read, random read, sequential write
      - BS: 4K, 8K, 16K, 32K, 64K, 128K
      - Sequential write and sequential read specific:
        - Number of parallel jobs: 1, 2, 4, 8, 14, 16, 32, 64, 128 (skipping entries > max_open_zones)
        - QD: 1
        - ioengine: psync
      - Random read specific:
        - QD: 1, 2, 4, 8, 14, 16, 32, 64, 128
        - ioengine: io_uring

    For reads the drive is prepared with a write. The ZBD is reset before each
    run.

  - Generated csv output file is fio_zone_throughput_avg_lat.csv
    1. avg_lat_us: Average latency in µs for the specific run.
    2. throughput_MiBs: Throughput in MiBs for the specific run.
    3. clat_p1_us - clat_p100us: completion latency percentiles in µs.

  - Generates multiple graphs that plot the behavior of throughput and latency.

## usenix_atc_2021_zns_eval
  Executes RocksDB's db_bench according to the RocksDB evaluation section
  (5.2 RocksDB) of the paper '[ZNS: Avoiding the Block Interface Tax for
  Flash-based SSDs](https://www.pdl.cmu.edu/PDL-FTP/Storage/USENIX_ATC_2021_ZNS.pdf)'.

  Depending on if the specified drive to benchmark is a ZNS or Conventional
  device different benchmarks are run.
  - For conventional devices the db_bench workload is run on the following
    filesystems:
        - xfs
        - f2fs
  - For ZNS devices the db_bench workload is run on the f2fs filesystem and
    with the ZenFS RocksDB plugin without an additional filesystem.

  Note: the tests are designed to run on 2TB devices.

Advance Data Analysis using SQLite
----------------------
Benchmarks can implement to collect their CSV report into a SQLite database.
See `data_collector/sqlite_data_collector.py`

The database file `data-collection.sqlite3` will be created/modified in the
given output directory (by default `zbdbench_results`)

The database design is keeped in an easy format. Each ZBDBench benchmarking run
causes an entry in the `zbdbench_run` table which collects general system
information.
Each ZBDBench run can generate multiple results that are collected in a
benchmark specific table (e.g. `fio_zone_throughput_avg_lat`)

TODO: Add graph for the database layout

In case you want to connect your SQLite DB with Excel you need to install the
MySQL ODBC https://dev.mysql.com/downloads/connector/odbc/ .

On MacOS also install iOBDC http://www.iodbc.org/dataspace/doc/iodbc/wiki/iodbcWiki/Downloads .
Copy /usr/local/mysql-connector-odbc-8.0.12-macos10.13-x86-64bit to
/Library/ODBC and adjust /Library/ODBC/odbcinst.init
https://stackoverflow.com/questions/52896893/macos-connector-mysql-odbc-driver-could-not-be-loaded-in-excel-for-mac-2016 .

In the 'ODBC Data Source Administrator' a 'User DSN' needs to be created with the
following keywords and values:
```
SERVER <IP>
NO_SCHEMA 1
```

Within Excel in the 'Data' tab you can 'Get Data' 'From Database (Microsoft Query)' with
the specified 'User DSN' and the following query:

```
SELECT * FROM fio_zone_throughput_avg_lat INNER JOIN zbdbench_run ON fio_zone_throughput_avg_lat.zbdbench_run_id = zbdbench_run.id;
```
