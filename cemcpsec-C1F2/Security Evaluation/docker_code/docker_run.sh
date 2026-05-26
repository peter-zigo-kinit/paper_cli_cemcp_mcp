#! /bin/bash
: "${MCP_GATEWAY:="http://host.docker.internal:8080"}"
: "${RUN_DIR:="/var/folders/_v/8t3fqs6d1d35vgtybh045t440000gn/T/sand_box_run_test"}"
: "${IMAGE_NAME:="code_execution_sandbox:v2"}"
: "${CMD:="python -u /workspace/main.py"}"

 docker run --rm -it \
 -e MCP_GATEWAY=${MCP_GATEWAY} \
 -v ${RUN_DIR}:/workspace \
 ${IMAGE_NAME} \
 ${CMD}

