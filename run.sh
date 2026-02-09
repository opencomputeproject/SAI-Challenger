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
OPTS=""
COMMAND="start"
SAI_INTERFACE="redis"
BASE_OS="bookworm"

declare -A base_os_map
base_os_map["deb10"]="buster"
base_os_map["buster"]="buster"
declare -A base_os_map
base_os_map["deb10"]="buster"
base_os_map["buster"]="buster"
base_os_map["deb11"]="bullseye"
base_os_map["bullseye"]="bullseye"
base_os_map["deb12"]="bookworm"
base_os_map["bookworm"]="bookworm"
base_os_map["deb13"]="trixie"
base_os_map["trixie"]="trixie"


print-help() {
    echo
    echo "$(basename ""$0"") [OPTIONS]"
    echo "Options:"
    echo "  -h Print script usage"
    echo "  -i [standalone|client|server]"
    echo "     Image type to be started"
    echo "  -a ASIC"
    echo "     ASIC to be tested"
    echo "  -t TARGET"
    echo "     Target device with this NPU"
    echo "  -c [start|stop]"
    echo "     Start or stop docker. Default (start)"
    echo "  -p Run Docker in --privileged mode"
    echo "  -n Run Docker with host networking namespace"
    echo "  -r Remove Docker after run"
    echo "  -s [redis|thrift]"
    echo "     SAI interface"
    echo "  -o [buster|bullseye|bookworm|trixie]"
    echo "     Docker image base OS"
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
        "-p")
            OPTS="$OPTS --privileged"
        ;;
        "-r")
            OPTS="$OPTS --rm"
        ;;
        "-n")
            OPTS="$OPTS --network host"
        ;;
        "-c")
            COMMAND="$2"
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
        *)
            # Starting from the first unknown parameter,
            # pass all parameters as a docker run options.
            while [[ $# -gt 0 ]]; do
                if [ -z "${OPTS}" ]; then
                    OPTS=${1}
                elif [[ ${1} = *" "* ]]; then
                    # parameter contains spaces
                    # E.g., docker run ... --shm-size=256m -v /some/path/:/some/path/:rw
                    OPTS="${OPTS} \"${1}\""
                else
                    OPTS="${OPTS} ${1}"
                fi
                shift
            done
            break
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

print-start-options() {
    echo
    echo "==========================================="
    echo "     SAI Challenger ${COMMAND} options"
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

trap print-start-options EXIT

start_docker_container() {
    if [ -z "$(docker images -q ${IMG_NAME}:${BASE_OS})" ]; then
        docker pull plvisiondevs/${IMG_NAME}:${BASE_OS}-latest
        docker tag plvisiondevs/${IMG_NAME}:${BASE_OS}-latest ${IMG_NAME}:${BASE_OS}
    fi
    docker run --name ${IMG_NAME}-run \
        --cap-add=NET_ADMIN \
        --device /dev/net/tun:/dev/net/tun \
        ${OPTS} \
        -d "${IMG_NAME}:${BASE_OS}"
}

stop_docker_container() {
    DOCKER_NAME=${IMG_NAME}-run
    PID=$(docker inspect --format '{{ .State.Pid }}' $DOCKER_NAME)
    NETNS="$DOCKER_NAME_$PID"
    docker stop $DOCKER_NAME
    # Remove NetNS symbolic link if any
    [ -L /var/run/netns/$NETNS ] && sudo rm /var/run/netns/$NETNS
}

if [ "${SAI_INTERFACE}" = "thrift" ]; then
    PREFIX="sc-thrift"
else
    PREFIX="sc"
fi


if [ "${IMAGE_TYPE}" = "standalone" ]; then
    IMG_NAME=$(echo "${PREFIX}-${ASIC_TYPE}-${TARGET}" | tr '[:upper:]' '[:lower:]')
    OPTS="$OPTS -v $(pwd):/sai-challenger"
elif [ "${IMAGE_TYPE}" = "server" ]; then
    IMG_NAME=$(echo "${PREFIX}-server-${ASIC_TYPE}-${TARGET}" | tr '[:upper:]' '[:lower:]')
else
    IMG_NAME=${PREFIX}-client
    OPTS="$OPTS -v $(pwd):/sai-challenger"
fi

if [ "${COMMAND}" = "start" ]; then
    start_docker_container
elif [ "${COMMAND}" = "stop" ]; then
    stop_docker_container
else
    echo "Unknown command \"${COMMAND}\". Supported: start|stop."
fi
