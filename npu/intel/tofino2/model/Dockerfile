FROM sc-base

MAINTAINER andriy.kokhan@gmail.com

ENV SC_PLATFORM=intel
ENV SC_ASIC=tofino2
ENV SC_TARGET=model

WORKDIR /sai

RUN apt-get install -y libgoogle-perftools4

COPY *.deb /sai/
RUN dpkg -i *.deb

RUN git clone https://github.com/sonic-net/sonic-sairedis.git \
        && cd sonic-sairedis \
        && . /sai.env \
        && git checkout ${SAIREDIS_ID} \
        && git submodule update --init --recursive \
        && cd SAI && git fetch origin \
        && git checkout ${SAI_ID} \
        && git submodule update --init --recursive \
        && cp meta/saimetadatautils.c /sai/gen_attr_list/ \
        && cp meta/saimetadata.c /sai/gen_attr_list/ \
        && cp meta/saiserialize.c /sai/gen_attr_list/ \
        && cd .. \
        # Exclude sairedis tests that require Redis to be running
        && find . -type f -name Makefile.am | xargs sed -ri 's/^TESTS =/# TESTS =/' \
        && ./autogen.sh \
        && dpkg-buildpackage -us -uc -b --target=binary-syncd --jobs=auto \
        && cd .. \
        && dpkg -i libsaimetadata_1.0.0_amd64.deb \
        && dpkg -i libsaimetadata-dev_1.0.0_amd64.deb \
        && dpkg -i libsairedis_1.0.0_amd64.deb \
        && dpkg -i libsairedis-dev_1.0.0_amd64.deb \
        && dpkg -i syncd_1.0.0_amd64.deb \
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
        && python -mjson.tool /etc/sai/sai.json.tmp > /etc/sai/sai.json \
        && rm /etc/sai/sai.json.tmp

# Setup supervisord
COPY scripts/redis_start.sh   /usr/bin/redis_start.sh
COPY scripts/model_start.sh   /usr/bin/model_start.sh
COPY scripts/syncd_start.sh   /usr/bin/syncd_start.sh
COPY scripts/veth-create.sh   /usr/bin/veth-create.sh
COPY configs/ports.json                /usr/share/sonic/hwsku/ports.json
COPY configs/switch-sai-cpu-veth.conf  /usr/share/sonic/hwsku/switch-tna-sai.conf
COPY configs/supervisord.conf          /etc/supervisor/conf.d/supervisord.conf

WORKDIR /sai-challenger/tests

CMD ["/usr/bin/supervisord"]

