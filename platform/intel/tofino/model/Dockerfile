FROM sc-base

MAINTAINER andriy.kokhan@gmail.com

ENV SC_PLATFORM=intel
ENV SC_ASIC=tofino
ENV SC_TARGET=model

WORKDIR /sai

RUN apt-get install -y libgoogle-perftools4

COPY *.deb /sai/
RUN dpkg -i *.deb

RUN git clone https://github.com/Azure/sonic-sairedis.git \
        && cd sonic-sairedis \
        && . /sai.env \
        && git checkout ${SAIREDIS_ID} \
        && git submodule update --init --recursive \
        && cd SAI && git fetch origin \
        && git checkout ${SAI_ID} \
        && git submodule update --init --recursive \
        && cd .. \
        && ./autogen.sh && ./configure && make -j4 \
        && make install && ldconfig \
        && mkdir -p /usr/include/sai \
        && mv SAI/experimental  /usr/include/sai/experimental \
        && mv SAI/inc  /usr/include/sai/inc \
        && mkdir -p /usr/include/sai/meta \
        && cp SAI/meta/*.h  /usr/include/sai/meta/ \   
        && mv tests .. && rm -rf * && mv ../tests .


# Build attr_list_generator and generate /etc/sai/sai.json
RUN cd /sai/gen_attr_list \
        && mkdir build && cd build \
        && cmake .. \
        && make -j$(nproc) \
        && mkdir -p /etc/sai \
        && ./attr_list_generator > /etc/sai/sai.json

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

