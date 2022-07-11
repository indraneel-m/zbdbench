FROM fedora:36 AS stage1

MAINTAINER Indraneel M <Indraneel.Mukherjee@wdc.com>

ARG VERSION=fio-3.30

COPY blkzoned.h /root/blkzoned.h

RUN dnf install -y libaio git && \
	dnf install -y \
	libaio-devel \
	zlib-devel \
	make \
	automake \
	gcc \
	gcc-c++ \
	kernel-headers \
	coreutils && \
	dnf group install -y "C Development Tools and Libraries" "Development Tools" && \
	mv /root/blkzoned.h /usr/include/linux/blkzoned.h && \
	git clone https://github.com/axboe/fio.git -b "$VERSION" /root/fio && \
	cd /root/fio && \
	./configure && \
	make -j "$(nproc)" && \
	make install

RUN cd /root && \
	dnf install -y vim && \
	git clone https://github.com/indraneel-m/spdk.git /root/spdk && \
	cd spdk && \
	git switch uring-zns-spdk && \
	git submodule update --init && \
	./scripts/pkgdep.sh --all && \
	./configure --with-fio=/root/fio --with-uring --with-uring-zns && \
	make -j4 && \
	mkdir -p /root/spdk_bin/build && \
	cp -a include /root/spdk_bin &&\
	cp -a scripts /root/spdk_bin && \
	cp -a build/fio /root/spdk_bin/build/

COPY bdev_zoned_uring.json /root/spdk_bin/examples/bdev/fio_plugin/

COPY spdk_pre_setup.sh /root/spdk_bin/
RUN chmod +x /root/spdk_bin/spdk_pre_setup.sh


RUN cd / && \
	rm -rf /root/fio && \
	rm -rf /root/spdk && \
	dnf group remove -y "C Development Tools and Libraries" "Development Tools" && \
	dnf remove -y gcc gcc-c++ kernel-headers make automake && \
	dnf clean all

ENTRYPOINT ["/root/spdk_bin/spdk_pre_setup.sh"]
