#!/bin/bash

SAIC_HOME=.
TG=ptf
TARGET=saivs
ASIC_TYPE=trident2

while getopts "hat" OPT; do
    case ${OPT} in
    h)
        echo "Setup docker based testbed: 1) start client docker; 2) start server docker; 3) create links."
        echo "Usage: tb_ctl.sh [-a ASIC] [-t TARGET] COMMAND"
        echo -e "-h\tShow help"
        echo -e "-a\tSet ASIC. Default $ASIC_TYPE."
        echo -e "-t\tSet target. Default $TARGET."
        echo -e "COMMAND\tstart|stop"
        exit 0
        ;;
    a)
        ASIC_TYPE=$OPTARG
        echo "ASIC type: ${ASIC_TYPE}"
        ;;
    t)
        TARGET=$OPTARG
        echo "Target: ${TARGET}"
        ;;
    *)
        echo "Invalid options"
        exit 1
        ;;
    esac
done

COMMAND=${@: -1}
[[ ! ${COMMAND} =~ start|stop ]] && {
    echo "Incorrect COMMAND provided. Allowed: start|stop"
    exit 1
}

start_all() {
    $SAIC_HOME/run.sh -i client -c start -r
    $SAIC_HOME/run.sh -i server -c start -a $ASIC_TYPE -t $TARGET -r -p
    sudo $SAIC_HOME/veth-create-host.sh sc-server-${ASIC_TYPE}-${TARGET}-run sc-client-run
}

stop_all() {
  $SAIC_HOME/run.sh -i server -c stop -a $ASIC_TYPE -t $TARGET
  $SAIC_HOME/run.sh -i client -c stop
}

case $COMMAND in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
esac
