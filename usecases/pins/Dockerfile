ARG BASE_IMAGE=sc-trident2-saivs
ARG BASE_IMAGE_TAG=latest
FROM ${BASE_IMAGE}:${BASE_IMAGE_TAG}

LABEL Description="PINS Lite"
LABEL Vendor="PLVision LTD"
LABEL Version="0.1"

ENV DEBIAN_FRONTEND=noninteractive

COPY sai.env /
WORKDIR /sonic/src

# SONiC Orchagent
RUN apt-get install -y libjansson-dev
RUN git clone https://github.com/sonic-net/sonic-swss \
        && cd sonic-swss \
        && echo "SUBDIRS = neighsyncd portsyncd fdbsyncd orchagent swssconfig cfgmgr" > Makefile.am \
        && . /sai.env \
        && git checkout ${SWSS_ID} \
        && git submodule update --init --recursive \
        && ./autogen.sh && ./configure \
        && make -j$(nproc) && make install \
        && cd .. \
        && rm -rf sonic-swss

# P4RT dependencies
RUN curl -fsSL -o /usr/local/bin/bazel https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-linux-amd64 \
        && chmod 755 /usr/local/bin/bazel

RUN apt-get install -y libgmp-dev
COPY Makefile /sonic/src/sonic-p4rt/

# P4RT
ENV CONFIGURED_ARCH=amd64
ENV SONIC_P4RT_VERSION="0.0.1"
ENV SONIC_P4RT="sonic-p4rt_${SONIC_P4RT_VERSION}_${CONFIGURED_ARCH}.deb"
WORKDIR /sonic/src/sonic-p4rt

RUN cd /sonic/src \
        && git clone --recursive https://github.com/Azure/sonic-swss-common \
        && cd sonic-swss-common \
        && . /sai.env \
        && git checkout ${SWSS_COMMON_ID} \
        && cd /sonic/src/sonic-p4rt \
        && git clone --recursive https://github.com/sonic-net/sonic-pins \
        && cd sonic-pins \
        && git checkout ${PINS_ID} \
        && cd - \
        && make -j$(nproc) \
        && cd / \
        && dpkg -i ${SONIC_P4RT} \
        && rm -rf /sonic ${SONIC_P4RT} \
        && rm -rf /root/.cache/bazel*

WORKDIR /sai-challenger

# Setup supervisord
COPY configs/supervisord-pins.conf  /etc/supervisor/conf.d/
COPY scripts/orchagent.sh           /usr/local/bin/
COPY scripts/p4rt.sh                /usr/bin/

CMD ["/usr/bin/supervisord"]

