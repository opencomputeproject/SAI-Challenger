#!/usr/bin/env bash

#
# Clean up SAI-VPP state and start syncd.
#

set -euo pipefail

PROFILE="${SYNCD_PROFILE:-/etc/sai.d/sai.profile}"
VPP_API_TIMEOUT=60

ARGS=(-s)

echo "SAI-VPP: starting syncd"

echo "Restarting VPP..."
supervisorctl restart vpp

if ! supervisorctl restart vpp; then
    echo "ERROR: Failed to restart VPP"
    exit 1
fi


if [ -f "${PROFILE}" ]; then
    ARGS+=(-p "${PROFILE}")
fi

vpp_api_check()
{
    local VPP_API_SOCK=$1
    local ELAPSED=0

    while (( ELAPSED < VPP_API_TIMEOUT )); do
        if [ -S "${VPP_API_SOCK}" ] &&
           timeout 5s vpp_api_test socket-name "${VPP_API_SOCK}" \
               <<< "show_version" 2>/dev/null |
           grep -q "version:"
        then
            echo "VPP API is ready."
            return 0
        fi

        sleep 1
        ((ELAPSED+=1))
    done
}

echo "Waiting for VPP API..."

vpp_api_check /run/vpp/api.sock

echo "Resetting VPP host interfaces..."

/usr/bin/vpp_hostif_reset.sh

echo "VPP is ready, starting syncd..."

exec /usr/bin/syncd "${ARGS[@]}" "$@"