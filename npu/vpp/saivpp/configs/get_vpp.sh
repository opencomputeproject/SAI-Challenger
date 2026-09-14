#!/bin/bash
set -e

VPP_VERSION_SONIC="2606-0.2+b1sonic1"
CONFIGURED_ARCH="amd64"

VPP_DEB_URL="https://packages.buildkite.com/sonic-vpp/vpp/any/pool/any/main/v/vpp"

DEST="/tmp/vpp-artifacts"

mkdir -p "$DEST"

VPP_DEBS=(
    "libvppinfra_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "vpp_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "vpp-plugin-core_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "vpp-plugin-dpdk_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "vpp-plugin-devtools_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "vpp-dev_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "libvppinfra-dev_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
    "vpp-dbg_${VPP_VERSION_SONIC}_${CONFIGURED_ARCH}.deb"
)

echo "Trying to download pre-built VPP packages..."

DOWNLOAD_FAILED=0

for deb in "${VPP_DEBS[@]}"; do
    echo "Downloading $deb..."

    if ! curl -L -f -o "$DEST/$deb" "$VPP_DEB_URL/$deb"; then
        echo "Failed to download $deb"
        DOWNLOAD_FAILED=1
        break
    fi
done

if [ "$DOWNLOAD_FAILED" -eq 0 ]; then
    echo "All pre-built VPP packages downloaded successfully."
    exit 0
fi


echo "Pre-built VPP packages are unavailable."
echo "Falling back to local VPP build..."

rm -rf "$DEST"
mkdir -p "$DEST"

git clone --filter=blob:none \
    https://github.com/sonic-net/sonic-platform-vpp.git \
    /tmp/sonic-platform-vpp

cd /tmp/sonic-platform-vpp
git checkout a38dedf

cd vppbld

make build_locally \
    DEST="$DEST" \
    CONFIGURED_ARCH="$CONFIGURED_ARCH" \
    VPP_VERSION_SONIC="$VPP_VERSION_SONIC" \
    -f Makefile


echo "VPP build completed successfully."

