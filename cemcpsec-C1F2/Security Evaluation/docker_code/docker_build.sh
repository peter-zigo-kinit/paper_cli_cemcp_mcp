#!/bin/bash
# set variables
: "${IMAGE_NAME:="code_execution_sandbox"}"
: "${IMAGE_TAG:="latest"}"

# build the image
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
