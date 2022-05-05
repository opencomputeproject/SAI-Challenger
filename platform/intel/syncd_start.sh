#!/usr/bin/env bash
#
# Script to start syncd using supervisord
#

CMD=/usr/local/bin/syncd
CMD_ARGS=
# Set synchronous mode
CMD_ARGS+=" -s"
# Use bulk APIs in SAI
CMD_ARGS+=" -l"


HWSKU_DIR=/usr/share/sonic/hwsku

config_syncd()
{
    PROFILE_FILE="$HWSKU_DIR/sai.profile"
    if [ ! -f $PROFILE_FILE ]; then
        # default profile file
        PROFILE_FILE="/tmp/sai.profile"
        echo "SAI_KEY_WARM_BOOT_WRITE_FILE=/var/warmboot/sai-warmboot.bin" > $PROFILE_FILE
        echo "SAI_KEY_WARM_BOOT_READ_FILE=/var/warmboot/sai-warmboot.bin" >> $PROFILE_FILE
        echo "SAI_BFN_MODEL=1" >> $PROFILE_FILE
    fi
    CMD_ARGS+=" -p $PROFILE_FILE"

    # Check and load SDE profile
    #P4_PROFILE="x2_profile"
    #if [[ -n "$P4_PROFILE" ]]; then
    #    if [[ ( -d /opt/bfn/install_${P4_PROFILE} ) && ( -L /opt/bfn/install || ! -e /opt/bfn/install ) ]]; then
    #        ln -srfn /opt/bfn/install_${P4_PROFILE} /opt/bfn/install
    #    fi
    #fi
    export PYTHONHOME=/opt/bfn/install/
    export PYTHONPATH=/opt/bfn/install/
    #export ONIE_PLATFORM=`grep onie_platform /etc/machine.conf | awk 'BEGIN { FS = "=" } ; { print $2 }'`
    export ONIE_PLATFORM=
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/bfn/install/lib/platform/$ONIE_PLATFORM:/opt/bfn/install/lib:/opt/bfn/install/lib/tofinopd/switch
    /opt/bfn/install/bin/dma_setup.sh
}

config_syncd

exec ${CMD} ${CMD_ARGS}
