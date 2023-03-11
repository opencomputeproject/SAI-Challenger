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
EXEC_CMD=""
SAI_INTERFACE="redis"
TTY="-ti"

print-help() {
    echo
    echo "$(basename ""$0"") [OPTIONS] [command]"
    echo "Options:"
    echo "  -h Print script usage"
    echo "  -i [standalone|client|server]"
    echo "     Image type to be started"
    echo "  -a ASIC"
    echo "     ASIC to be tested"
    echo "  -t TARGET"
    echo "     Target device with this NPU"
    echo "  -s [redis|thrift]"
    echo "     SAI interface"
    echo
    echo "  --no-tty   Do not allocate a pseudo-TTY"
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
            if [ -z "${EXEC_CMD}" ]; then
                ASIC_TYPE="$2"
            else
                EXEC_CMD="${EXEC_CMD} ${1} ${2}"
            fi
            shift
        ;;
        "-t"|"--target")
            if [ -z "${EXEC_CMD}" ]; then
                TARGET="$2"
            else
                EXEC_CMD="${EXEC_CMD} ${1} ${2}"
            fi
            shift
        ;;
        "-s"|"--sai_interface")
            SAI_INTERFACE="$2"
            shift
        ;;
        "--no-tty")
            TTY=""
        ;;
        *)
            if [ -z "${EXEC_CMD}" ]; then
                EXEC_CMD=${1}
            elif [[ ${1} = *" "* ]]; then
                # parameter contains spaces
                EXEC_CMD="${EXEC_CMD} \"${1}\""
            else
                EXEC_CMD="${EXEC_CMD} ${1}"
            fi
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

if [ -z "${EXEC_CMD}" ]; then
    EXEC_CMD="bash"
fi

print-start-options() {
    echo
    echo "==========================================="
    echo "     SAI Challenger run options"
    echo "==========================================="
    echo
    echo " Docker image type  : ${IMAGE_TYPE}"

    if [ "${IMAGE_TYPE}" != "client" ]; then
        echo " ASIC name          : ${ASIC_TYPE}"
        echo " ASIC target        : ${TARGET}"
        echo " Platform path      : ${ASIC_PATH}"
        echo " SAI interface      : ${SAI_INTERFACE}"
    fi

    echo " Container name     : ${CONTAINER}"
    echo " Command            : ${EXEC_CMD}"
    echo
    echo "==========================================="
    echo
}

trap print-start-options EXIT

if [ "${SAI_INTERFACE}" = "thrift" ]; then
    PREFIX="sc-thrift"
else
    PREFIX="sc"
fi

# Start Docker container
if [ "${IMAGE_TYPE}" = "standalone" ]; then
    CONTAINER=$(echo "${PREFIX}-${ASIC_TYPE}-${TARGET}-run" | tr '[:upper:]' '[:lower:]')
elif [ "${IMAGE_TYPE}" = "server" ]; then
    CONTAINER="sc-server-${ASIC_TYPE}-${TARGET}-run"
else
    CONTAINER="${PREFIX}-client-run"
fi
docker exec ${TTY} ${CONTAINER} bash -c "${EXEC_CMD}"
