ARG BASE_OS=trixie
FROM sc-base:${BASE_OS}

MAINTAINER maksym.parfeniuk.dev@gmail.com

ENV SC_PLATFORM=vpp
ENV SC_ASIC=vpp
ENV SC_TARGET=saivpp

WORKDIR /sai

ENV VPP_INSTALL_SKIP_SYSCTL=1
COPY configs/get_vpp.sh /tmp/get_vpp.sh
RUN mkdir -p /var/log/vpp /run/vpp /etc/vpp \
    && chmod +x /tmp/get_vpp.sh \
    && /tmp/get_vpp.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/vpp-artifacts/*.deb \
    && ldconfig \
    && rm -rf /tmp/sonic-platform-vpp /tmp/vpp-artifacts /tmp/get_vpp.sh /var/lib/apt/lists/*

# Verify VPP libs
RUN set -eux; \
    vpp --version; \
    ldconfig -p | grep libvlib; \
    ldconfig -p | grep libvlibapi; \
    ldconfig -p | grep libvppapiclient; \
    ldconfig -p | grep libvlibmemoryclient; \
    ldconfig -p | grep libvppinfra; \
    test -f /usr/include/vpp_plugins/tunterm_acl/tunterm_acl.api_enum.h; \
    test -f /usr/include/vpp_plugins/tunterm_acl/tunterm_acl.api_types.h

# Clone, prepare, configure and build sonic-sairedis
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
    && cd ../.. \
    && GCC_VER=$(gcc -dumpversion | cut -d. -f1) \
    && if [ "$GCC_VER" -ge 14 ]; then \
            # Fix C++20 template-id constructor syntax (GCC 14 / Debian 13)
            sed -i 's/ConcurrentQueue<T>(const ConcurrentQueue<T>&)/ConcurrentQueue(const ConcurrentQueue<T>\&)/' syncd/ConcurrentQueue.h; \
            # Fix missing cstdint include (GCC 14 / Debian 13)
            sed -i '/#include <string>/a #include <cstdint>' syncd/RequestShutdownCommandLineOptions.h; \
        fi \
    && find . -type f -name Makefile.am | xargs sed -ri 's/^TESTS =/# TESTS =/' \
    && sed -i \
        's/^SUBDIRS = py2 py3/SUBDIRS = py3/' pyext/Makefile.am \
    && ./autogen.sh \
    # Disable -Werror=overloaded-virtual and -Werror=template-id-cdtor for GCC 14
    && GCC_VER=$(gcc -dumpversion | cut -d. -f1) \
    && if [ "$GCC_VER" -ge 14 ]; then \
            export DEB_CXXFLAGS_APPEND="-Wno-error=overloaded-virtual -Wno-error=template-id-cdtor"; \
        else \
            export DEB_CXXFLAGS_APPEND="-Wno-error=overloaded-virtual"; \
        fi \
    && dpkg-buildpackage -us -uc -b -Psyncd,vs,nopython2 --jobs=auto \
    && cd .. \
    && dpkg -i libsaimetadata_1.0.0_amd64.deb \
    && dpkg -i libsaimetadata-dev_1.0.0_amd64.deb \
    && dpkg -i libsairedis_1.0.0_amd64.deb \
    && dpkg -i libsaivs_1.0.0_amd64.deb \
    && dpkg -i libsaivs-dev_1.0.0_amd64.deb \
    && dpkg -i syncd-vs_1.0.0_amd64.deb \
    && mv sonic-sairedis/tests . \
    && rm -f *.deb \
    && rm -rf sonic-sairedis/* \
    && mv tests sonic-sairedis/     

# Verify libsaivs links against VPP
RUN set -eux; \
    LIBSAIVS="$(ldconfig -p | awk '/libsaivs\.so/{print $NF; exit}')"; \
    test -n "$LIBSAIVS"; \
    echo "libsaivs: $LIBSAIVS"; \
    ldd "$LIBSAIVS" | grep -E \
        'libvlib|libvlibapi|libvppapiclient|libvlibmemoryclient|libvppinfra'

# Build SAI attributes metadata JSON generator and generate /etc/sai/sai.json
RUN cd /sai/gen_attr_list \
    && mkdir build && cd build \
    && cmake .. \
    && make -j$(nproc) \
    && mkdir -p /etc/sai \
    && ./attr_list_generator > /etc/sai/sai.json.tmp \
    && python3 -m json.tool /etc/sai/sai.json.tmp > /etc/sai/sai.json \
    && rm -f /etc/sai/sai.json.tmp

# Runtime
RUN mkdir -p /etc/vpp

COPY configs/sonic_vpp_ifmap.ini /usr/share/sonic/hwsku/sonic_vpp_ifmap.ini
COPY configs/vpp_veth_create.sh /usr/bin/vpp_veth_create.sh
COPY configs/startup.conf /etc/vpp/startup.conf
COPY configs/sai.profile       /etc/sai.d/sai.profile
COPY configs/lanemap.ini       /usr/share/sonic/hwsku/lanemap.ini
COPY configs/supervisord.conf  /etc/supervisor/conf.d/supervisord.conf
COPY configs/syncd_startup.sh /usr/bin/syncd_startup.sh
COPY configs/vpp_hostif_reset.sh /usr/bin/vpp_hostif_reset.sh

WORKDIR /sai-challenger/tests

CMD ["/usr/bin/supervisord"]