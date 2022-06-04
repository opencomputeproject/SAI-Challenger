FROM sc-base

MAINTAINER andriy.kokhan@gmail.com

ENV SC_PLATFORM=broadcom
ENV SC_ASIC=BCM56850
ENV SC_TARGET=saivs

WORKDIR /sai

RUN git clone https://github.com/Azure/sonic-sairedis.git \
        && cd sonic-sairedis \
        && . /sai.env \
        && git checkout ${SAIREDIS_ID} \
        && git submodule update --init --recursive \
        && cd SAI && git fetch origin \
        && git checkout ${SAI_ID} \
        && git submodule update --init --recursive \
        && cd .. \
        && ./autogen.sh && ./configure --with-sai=vs && make -j4 \
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
COPY configs/sai.profile       /etc/sai.d/sai.profile
COPY configs/lanemap.ini       /usr/share/sonic/hwsku/lanemap.ini
COPY configs/supervisord.conf  /etc/supervisor/conf.d/supervisord.conf

WORKDIR /sai-challenger/tests

CMD ["/usr/bin/supervisord"]

