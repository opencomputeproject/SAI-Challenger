ARG BASE_OS
FROM sc-base:${BASE_OS}

MAINTAINER andriy.kokhan@gmail.com

ENV SC_PLATFORM=broadcom
ENV SC_ASIC=BCM56850
ENV SC_TARGET=saivs

WORKDIR /sai

RUN git clone https://github.com/sonic-net/sonic-sairedis.git \
        && cd sonic-sairedis \
        && . /sai.env \
        && git checkout ${SAIREDIS_ID} \
        && git submodule update --init \
        && cd SAI && git fetch origin \
        && git checkout ${SAI_ID} \
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
        # Exclude sairedis tests that require Redis to be running
        && find . -type f -name Makefile.am | xargs sed -ri 's/^TESTS =/# TESTS =/' \
        && sed -i "s/^SUBDIRS = py2 py3/SUBDIRS = py3/" pyext/Makefile.am \
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

# Build SAI attributes metadata JSON generator and generate /etc/sai/sai.json
RUN cd /sai/gen_attr_list \
        && mkdir build && cd build \
        && cmake .. \
        && make -j$(nproc) \
        && mkdir -p /etc/sai \
        && ./attr_list_generator > /etc/sai/sai.json.tmp \
        && python3 -mjson.tool /etc/sai/sai.json.tmp > /etc/sai/sai.json \
        && rm /etc/sai/sai.json.tmp

# Setup supervisord
COPY configs/sai.profile       /etc/sai.d/sai.profile
COPY configs/lanemap.ini       /usr/share/sonic/hwsku/lanemap.ini
COPY configs/supervisord.conf  /etc/supervisor/conf.d/supervisord.conf

WORKDIR /sai-challenger/tests

CMD ["/usr/bin/supervisord"]
