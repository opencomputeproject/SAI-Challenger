#!/usr/bin/env bash

#
# Clean up SAI-VPP state and start syncd.
#

set -euo pipefail

PROFILE="${SYNCD_PROFILE:-/etc/sai.d/sai.profile}"

ARGS=(-s)

echo "SAI-VPP: starting syncd"

if [ -f "${PROFILE}" ]; then
    ARGS+=(-p "${PROFILE}")
fi

vpp_api_check()
{
    local VPP_API_SOCK=$1

    while true; do
        if [ -S "$VPP_API_SOCK" ] &&
           vpp_api_test socket-name "$VPP_API_SOCK" <<< "show_version" 2>/dev/null |
           grep -q "version:"
        then
            break
        fi

        sleep 1
    done
}

echo "Waiting for VPP API..."

vpp_api_check /run/vpp/api.sock

echo "Resetting VPP host interfaces..."

/usr/bin/vpp_hostif_reset.sh

echo "VPP is ready, starting syncd..."

exec /usr/bin/syncd "${ARGS[@]}" "$@"