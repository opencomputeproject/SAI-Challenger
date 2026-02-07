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
        # Apply Debian 13 metadata generation fix from upstream SAI
        # https://github.com/opencomputeproject/SAI/commit/56c9c039666b0d8bc40e8ff04c048d7b0e39ca75
        && wget -O /tmp/sai-deb13-fix.patch https://github.com/opencomputeproject/SAI/commit/56c9c039666b0d8bc40e8ff04c048d7b0e39ca75.patch \
        && git apply /tmp/sai-deb13-fix.patch \
        && rm /tmp/sai-deb13-fix.patch \
        && cd meta \
        && make saimetadata.h \
        && make saimetadata.c \
        && cp saimetadatautils.c /sai/gen_attr_list/ \
        && cp saimetadata.c /sai/gen_attr_list/ \
        && cp saiserialize.c /sai/gen_attr_list/ \
        && cd ../.. \
        # Exclude sairedis tests that require Redis to be running
        && find . -type f -name Makefile.am | xargs sed -ri 's/^TESTS =/# TESTS =/' \
        && sed -i "s/^SUBDIRS = py2 py3/SUBDIRS = py3/" pyext/Makefile.am \
        && ./autogen.sh \
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
