#!/usr/bin/env bash
#
# Script to start Tofino Model using supervisord
#

if [ $(pgrep -x syncd | wc -l) = "1" ]; then
    killall -q syncd
fi

sed -i "s/sudo env/exec env/g" /opt/bfn/install/bin/run_tofino_model.sh
exec /opt/bfn/install/bin/run_tofino_model.sh -q -p switch \
    -c /usr/share/sonic/hwsku/switch-tna-sai.conf \
    -f /usr/share/sonic/hwsku/ports.json \
    --arch tofino2
