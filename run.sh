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
    esac
    shift
done

if [[ "${IMAGE_TYPE}" != "standalone" && \
      "${IMAGE_TYPE}" != "client" && \
      "${IMAGE_TYPE}" != "server" ]]; then
    echo "Unknown image type \"${IMAGE_TYPE}\""
    exit 1
fi

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
    echo " ASIC name          : ${ASIC_TYPE}"
    echo " ASIC target        : ${TARGET}"
    echo " Platform path      : ${ASIC_PATH}"
    echo " SAI interface      : ${SAI_INTERFACE}"
    echo
    echo "==========================================="
    echo
}

trap print-start-options EXIT

stop_docker_container() {
    DOCKER_NAME=$1
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

if [ "${COMMAND}" = "start" ]; then

    # Start Docker container
    if [ "${IMAGE_TYPE}" = "standalone" ]; then
        IMG_NAME=$(echo "${PREFIX}-${ASIC_TYPE}-${TARGET}" | tr '[:upper:]' '[:lower:]')
        docker run --name ${IMG_NAME}-run \
            -v $(pwd):/sai-challenger \
            --cap-add=NET_ADMIN \
            ${OPTS} \
            --device /dev/net/tun:/dev/net/tun \
            -d ${IMG_NAME}
    elif [ "${IMAGE_TYPE}" = "server" ]; then
        docker run --name sc-server-${ASIC_TYPE}-${TARGET}-run \
            --cap-add=NET_ADMIN \
            ${OPTS} \
            --device /dev/net/tun:/dev/net/tun \
            -d sc-server-${ASIC_TYPE}-${TARGET}
    else
        docker run --name ${PREFIX}-client-run \
            -v $(pwd):/sai-challenger \
            --cap-add=NET_ADMIN \
            --device /dev/net/tun:/dev/net/tun \
            ${OPTS} \
            -d ${PREFIX}-client
    fi

elif [ "${COMMAND}" = "stop" ]; then

    # Stop Docker container
    if [ "${IMAGE_TYPE}" = "standalone" ]; then
        stop_docker_container ${PREFIX}-${ASIC_TYPE}-${TARGET}-run
    elif [ "${IMAGE_TYPE}" = "server" ]; then
        stop_docker_container sc-server-${ASIC_TYPE}-${TARGET}-run
    else
        stop_docker_container ${PREFIX}-client-run
    fi

else
    echo "Unknown command \"${COMMAND}\". Supported: start|stop."
fi
