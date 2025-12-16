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
BASE_OS="buster"
NOSNAPPI=""
GIT_UNAME=""
GIT_TOKEN=""

declare -A base_os_map
base_os_map["deb10"]="buster"
base_os_map["buster"]="buster"
base_os_map["deb11"]="bullseye"
base_os_map["bullseye"]="bullseye"
base_os_map["deb12"]="bookworm"
base_os_map["bookworm"]="bookworm"


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
    echo "  -o [buster|bullseye|bookworm]"
    echo "     Docker image base OS"
    echo "  -g [uname git_hub_token]"
    echo "     Provide the private repository user name and token"
    echo "  --nosnappi"
    echo "     Do not include snappi to the final image"
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
        "-o"|"--base_os")
            BASE_OS="$2"
            shift
        ;;
        "-g"|"--git_login")
            GIT_UNAME="$2"
            GIT_TOKEN="$3"
            shift 2
        ;;
        "--nosnappi")
            NOSNAPPI="y"
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

if [ ! -v base_os_map["${BASE_OS}"] ]; then
    echo "Unknown base OS \"${BASE_OS}\""
    exit 1
fi

BASE_OS="${base_os_map[${BASE_OS}]}"

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
    echo " Base OS            : ${BASE_OS}"
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
    docker build -f dockerfiles/${BASE_OS}/Dockerfile \
        --build-arg GIT_UNAME="${GIT_UNAME}" \
        --build-arg GIT_TOKEN="${GIT_TOKEN}" \
        -t sc-base:${BASE_OS} .
elif [ "${IMAGE_TYPE}" = "server" ]; then
    find ${ASIC_PATH}/../ -type f -name \*.py -exec install -D {} .build/{} \;
    find ${ASIC_PATH}/../ -type f -name \*.json -exec install -D {} .build/{} \;
    if [ "${SAI_INTERFACE}" = "thrift" ]; then
        docker build -f dockerfiles/${BASE_OS}/Dockerfile.saithrift-server \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-thrift-server-base:${BASE_OS} .
    else
        docker build -f dockerfiles/${BASE_OS}/Dockerfile.server \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-server-base:${BASE_OS} .
    fi
    rm -rf .build/
else
    docker build -f dockerfiles/${BASE_OS}/Dockerfile.client \
        --build-arg NOSNAPPI=${NOSNAPPI} \
        --build-arg GIT_UNAME="${GIT_UNAME}" \
        --build-arg GIT_TOKEN="${GIT_TOKEN}" \
        -t sc-client:${BASE_OS} .
    if [ "${SAI_INTERFACE}" = "thrift" ]; then
        docker build -f dockerfiles/${BASE_OS}/Dockerfile.saithrift-client \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-thrift-client:${BASE_OS} .
    fi
    exit 0
fi

# Build target Docker image
pushd "${ASIC_PATH}/${TARGET}"
IMG_NAME=$(echo "${ASIC_TYPE}-${TARGET}" | tr '[:upper:]' '[:lower:]')
if [ "${IMAGE_TYPE}" = "standalone" ]; then
    if [ "${SAI_INTERFACE}" = "thrift" ]; then
        docker build -f Dockerfile.saithrift \
            --build-arg BASE_OS=${BASE_OS} \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-thrift-${IMG_NAME}:${BASE_OS} .
    else
        docker build -f Dockerfile \
            --build-arg BASE_OS="${BASE_OS}" \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-${IMG_NAME}:${BASE_OS} .
    fi
elif [ "${IMAGE_TYPE}" = "server" ]; then
    if [ "${SAI_INTERFACE}" = "thrift" ]; then
        docker build -f Dockerfile.saithrift-server \
            --build-arg BASE_OS=${BASE_OS} \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-thrift-server-${IMG_NAME}:${BASE_OS} .
    else
        docker build -f Dockerfile.server \
            --build-arg BASE_OS=${BASE_OS} \
            --build-arg GIT_UNAME="${GIT_UNAME}" \
            --build-arg GIT_TOKEN="${GIT_TOKEN}" \
            -t sc-server-${IMG_NAME}:${BASE_OS} .
    fi
fi
popd
