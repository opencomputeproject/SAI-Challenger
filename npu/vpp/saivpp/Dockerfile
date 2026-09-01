ARG BASE_OS=bookworm
FROM sc-base:${BASE_OS}

LABEL maintainer="andriy.kokhan@gmail.com"

ENV SC_PLATFORM=vpp
ENV SC_ASIC=vpp
ENV SC_TARGET=saivpp

WORKDIR /sai

# ============================================================
# 1. Dependencies
# ============================================================
RUN mkdir -p /var/log/vpp /run/vpp



RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        sudo \
        ca-certificates \
        build-essential \
        autoconf \
        automake \
        libtool \
        libtool-bin \
        pkg-config \
        python3 \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        cmake \
        ninja-build \
        meson \
        bison \
        flex \
        rsync \
        file \
        unzip \
        xz-utils \
        lsb-release \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# 2. Build SONiC-patched VPP
# ============================================================

RUN git clone https://github.com/sonic-net/sonic-platform-vpp.git \
        /tmp/sonic-platform-vpp \
    && cd /tmp/sonic-platform-vpp/vppbld \
    && mkdir -p /tmp/vpp-artifacts \
    && make \
        build_locally \
        DEST=/tmp/vpp-artifacts \
        CONFIGURED_ARCH=amd64 \
        VPP_VERSION_SONIC=26.06-0.5+b1sonic1 \
        -f Makefile

# ============================================================
# 3. Install VPP
# ============================================================

RUN set -eux; \
    if [ -f /sbin/sysctl ]; then \
        mv /sbin/sysctl /sbin/sysctl.real; \
    elif [ -f /bin/sysctl ]; then \
        mv /bin/sysctl /bin/sysctl.real; \
    fi; \
    printf '#!/bin/sh\nexit 0\n' > /sbin/sysctl; \
    chmod +x /sbin/sysctl; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        /tmp/vpp-artifacts/*.deb; \
    if [ -f /sbin/sysctl.real ]; then \
        mv /sbin/sysctl.real /sbin/sysctl; \
    elif [ -f /bin/sysctl.real ]; then \
        mv /bin/sysctl.real /bin/sysctl; \
    else \
        rm -f /sbin/sysctl; \
    fi; \
    ldconfig; \
    rm -rf /tmp/sonic-platform-vpp /tmp/vpp-artifacts; \
    rm -rf /var/lib/apt/lists/*

# ============================================================
# 4. Verify VPP
# ============================================================

RUN set -eux; \
    vpp --version; \
    ldconfig -p | grep libvlib; \
    ldconfig -p | grep libvlibapi; \
    ldconfig -p | grep libvppapiclient; \
    ldconfig -p | grep libvlibmemoryclient; \
    ldconfig -p | grep libvppinfra; \
    test -f /usr/include/vpp_plugins/tunterm_acl/tunterm_acl.api_enum.h; \
    test -f /usr/include/vpp_plugins/tunterm_acl/tunterm_acl.api_types.h

# ============================================================
# 5. Clone pinned sonic-sairedis / SAI
# ============================================================

RUN git clone https://github.com/sonic-net/sonic-sairedis.git \
    && cd /sai/sonic-sairedis \
    && . /sai.env \
    && echo "SAIREDIS_ID=${SAIREDIS_ID}" \
    && echo "SAI_ID=${SAI_ID}" \
    && git checkout "${SAIREDIS_ID}" \
    && git submodule update --init --recursive \
    && cd SAI \
    && git fetch origin \
    && git checkout "${SAI_ID}" \
    && cd meta \
    && make saimetadata.h \
    && make saimetadata.c \
    && cp saimetadatautils.c /sai/gen_attr_list/ \
    && cp saimetadata.c /sai/gen_attr_list/ \
    && cp saiserialize.c /sai/gen_attr_list/ \
    && cd ../..

# ============================================================
# 6. Prepare sonic-sairedis
# ============================================================

RUN cd /sai/sonic-sairedis \
    && find . -type f -name Makefile.am \
       | xargs sed -ri 's/^TESTS =/# TESTS =/' \
    && sed -i \
       's/^SUBDIRS = py2 py3/SUBDIRS = py3/' \
       pyext/Makefile.am \
    && ./autogen.sh

# ============================================================
# 7. Configure + build
#
# USE_VPP is automatically enabled by configure when libvlib is found
# ============================================================

RUN cd /sai/sonic-sairedis \
    && ./configure \
        --with-sai=vs \
        --disable-python2 \
    && grep -E \
        'checking for main in -lvlib|VPP_LIBS|USE_VPP' \
        config.log \
    && make -j"$(nproc)"

# ============================================================
# 8. Build Debian packages
# ============================================================

RUN cd /sai/sonic-sairedis \
    && dpkg-buildpackage \
        -us \
        -uc \
        -b \
        -Psyncd,vs,nopython2 \
        --jobs=auto

# ============================================================
# 9. Install libsaivs + syncd-vs
# ============================================================

RUN cd /sai \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ./libsaimetadata_1.0.0_amd64.deb \
        ./libsaimetadata-dev_1.0.0_amd64.deb \
        ./libsairedis_1.0.0_amd64.deb \
        ./libsaivs_1.0.0_amd64.deb \
        ./libsaivs-dev_1.0.0_amd64.deb \
        ./syncd-vs_1.0.0_amd64.deb \
    && ldconfig \
    && rm -f /sai/*.deb \
    && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /etc/sai.d

COPY configs/sai.profile /etc/sai.d/sai.profile
# ============================================================
# 10. Verify libsaivs really links against VPP
# ============================================================

RUN set -eux; \
    LIBSAIVS="$(ldconfig -p | awk '/libsaivs\.so/{print $NF; exit}')"; \
    test -n "$LIBSAIVS"; \
    echo "libsaivs: $LIBSAIVS"; \
    ldd "$LIBSAIVS" | grep -E \
        'libvlib|libvlibapi|libvppapiclient|libvlibmemoryclient|libvppinfra'

# ============================================================
# 11. Generate SAI metadata
# ============================================================

RUN cd /sai/gen_attr_list \
    && mkdir -p build \
    && cd build \
    && cmake .. \
    && make -j"$(nproc)" \
    && mkdir -p /etc/sai \
    && ./attr_list_generator \
        > /etc/sai/sai.json.tmp \
    && python3 -m json.tool \
        /etc/sai/sai.json.tmp \
        > /etc/sai/sai.json \
    && rm -f /etc/sai/sai.json.tmp

# ============================================================
# 12. Runtime
# ============================================================

RUN mkdir -p /etc/vpp

COPY configs/vpp_veth_create.sh /usr/bin/vpp_veth_create.sh
COPY configs/startup.conf /etc/vpp/startup.conf
COPY configs/sai.profile       /etc/sai.d/sai.profile
COPY configs/lanemap.ini       /usr/share/sonic/hwsku/lanemap.ini
COPY configs/supervisord.conf  /etc/supervisor/conf.d/supervisord.conf



WORKDIR /sai-challenger/tests

CMD ["/usr/bin/supervisord"]