#!/bin/bash

# exit when any command fails
set -e

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo ERROR: "\"${last_command}\" command filed with exit code $?."' ERR

IMAGE_TYPE="standalone"
ASIC_TYPE=""
ASIC_PATH=""
TARGET=""
SAI_INTERFACE="redis"

print-help() {
    echo
    echo "$(basename ""$0"") [OPTIONS]"
    echo "Options:"
    echo "  -h Print script usage"
    echo "  -i [standalone|client|server]"
    echo "     Image type to be created"
    echo "  -a ASIC"
    echo "     ASIC to be tested"
    echo "  -t TARGET"
    echo "     Target device with this NPU"
    echo "  -s [redis|thrift]"
    echo "     SAI interface"
    echo
    exit 0
}

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        "-h"|"--help")
            print-help
            exit 0
        ;;
        "-i"|"--image")
            IMAGE_TYPE="$2"
            shift
        ;;
        "-a"|"--asic")
            ASIC_TYPE="$2"
            shift
        ;;
        "-t"|"--target")
            TARGET="$2"
            shift
        ;;
        "-s"|"--sai_interface")
            SAI_INTERFACE="$2"
            shift
        ;;
    esac
    shift
done

if [[ "${IMAGE_TYPE}" != "standalone" && \
      "${IMAGE_TYPE}" != "client" && \
      "${IMAGE_TYPE}" != "server" ]]; then
    echo "Unknown image type \"${IMAGE_TYPE}\""
    exit 1
fi

# Clean the previous build
rm -rf .build/

if [[ "${IMAGE_TYPE}" != "client" ]]; then

    if [ -z "${ASIC_TYPE}" ]; then
        ASIC_TYPE="trident2"
    fi

    ASIC_PATH=$(find -L -type d -name "${ASIC_TYPE}")
    if [ -z "${ASIC_PATH}" ]; then
        echo "Unknown ASIC type \"${ASIC_TYPE}\""
        exit 1
    fi

    if [ ! -z "${TARGET}" ]; then
        if [ ! -d "${ASIC_PATH}/${TARGET}" ]; then
            echo "Unknown target \"${TARGET}\""
            exit 1
        fi
    else
        # Get first folder as a default target
        TARGETS=( $(find -L "${ASIC_PATH}" -mindepth 1 -maxdepth 1 -type d) )
        TARGET="${TARGETS[0]}"
        if [ -z "${TARGET}" ]; then
            echo "Not able to find a default target..."
            exit 1
        fi
        TARGET=$(basename $TARGET)
    fi
fi

print-build-options() {
    echo
    echo "==========================================="
    echo "     SAI Challenger build options"
    echo "==========================================="
    echo
    echo " Docker image type  : ${IMAGE_TYPE}"
    echo " ASIC name          : ${ASIC_TYPE}"
    echo " ASIC target        : ${TARGET}"
    echo " Platform path      : ${ASIC_PATH}"
    echo " SAI interface      : ${SAI_INTERFACE}"     
    echo
    echo "==========================================="
    echo
}

trap print-build-options EXIT

# Build base Docker image
if [ "${IMAGE_TYPE}" = "standalone" ]; then
    docker build -f dockerfiles/Dockerfile -t sc-base .
elif [ "${IMAGE_TYPE}" = "server" ]; then
    find ${ASIC_PATH}/../ -type f -name \*.py -exec install -D {} .build/{} \;
    find ${ASIC_PATH}/../ -type f -name \*.json -exec install -D {} .build/{} \;
    docker build -f dockerfiles/Dockerfile.server -t sc-server-base .
    rm -rf .build/
else
    docker build -f dockerfiles/Dockerfile.client -t sc-client .
    if [ "${SAI_INTERFACE}" = "thrift" ]; then
        docker build -f dockerfiles/Dockerfile.saithrift-client -t sc-thrift-client .
    fi
fi

# Build target Docker image
pushd "${ASIC_PATH}/${TARGET}"
IMG_NAME=$(echo "${ASIC_TYPE}-${TARGET}" | tr '[:upper:]' '[:lower:]')
if [ "${IMAGE_TYPE}" = "standalone" ]; then
    if [ "${SAI_INTERFACE}" = "thrift" ]; then
        docker build -f Dockerfile.saithrift -t sc-thrift-${IMG_NAME} .
    else
        docker build -f Dockerfile -t sc-${IMG_NAME} .
    fi
elif [ "${IMAGE_TYPE}" = "server" ]; then
    docker build -f Dockerfile.server -t sc-server-${IMG_NAME} .
fi
popd
