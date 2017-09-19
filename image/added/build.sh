#!/bin/bash
# This script executes either a 'concreate build' or
# 'concreate generate; docker build -t <tag>' depending on whether or not an
# OUTPUT_IMAGE is specified or not.  The following variables are used by this
# script:
#       OUTPUT_IMAGE: optional.  The name of for the image being built.  If not
#               specified the default image name specified through concreate
#               will be used and the image will not be pushed to any repository.
#               This may be used for local builds.
#       OUTPUT_REGISTRY: optional.  The name of the registry to use for the tag.
#               This is used in conjunction with OUTPUT_IMAGE to generate the
#               tag, e.g. OUTPUT_REGISTRY/OUTPUT_IMAGE.
#       NO_PUSH: optional.  A non-empty value prevents the docker push
#               operation.
#       SOURCE_REPOSITORY: required.  The location of the source git repository
#               to clone.
#       SOURCE_REF: optional.  The git reference to use when building the image.
#       CONCREATE_CFG_PATH: optional.  The location of the .concreate
#               configuration file.
#       PUSH_DOCKERCFG_PATH: required to push image to target repository.
#               Specifies the path to the .docker/ directory containing the
#               docker configuration to be used during docker push.
#
# The following volumes locations may be required to build the image:
#       /var/run/docker.sock - This is required to build the image and can be
#               specified as '-v /var/run/docker.sock'.
#       CONCREATE_CFG_PATH - specify a volume to use your local configuration
#               file (typically ~/.concreate), where
#               CONCREATE_CFG_PATH == -v option.
#       PUSH_DOCKERCFG_PATH - specify a volume to use your local docker
#               configuration file (typically ~/.docker), where
#               PUSH_DOCKERCFG_PATH == -v option.
#       Additional .repo files - local files should be located in a sibling
#               directory next to .concreate when mounted in the image, e.g.
#               '-v ~/repos:${CONCREATE_CFG_PATH}/repos'
#
# Common issues:
#       Permission denied on mounted volumes: you may have to add :Z to the
#               volume parameters.
#        Cannot connect to the Docker daemon. Is the docker daemon running on
#               this host?: you may have to use the --privileged flag so the
#               container has access to the docker.sock.
#

set -o pipefail
IFS=$'\n\t'

DOCKER_SOCKET=/var/run/docker.sock

if [ ! -e "${DOCKER_SOCKET}" ]; then
  echo "Docker socket missing at ${DOCKER_SOCKET}"
  exit 1
fi

if [ -n "${OUTPUT_IMAGE}" ]; then
  TAG="${OUTPUT_REGISTRY:+${OUTPUT_REGISTRY}/}${OUTPUT_IMAGE}"
  echo "using tag: ${TAG}"
else
  echo "No output image specified.  Image will not be tagged."
fi

if [[ "${SOURCE_REPOSITORY}" = "http://*" ]] || [[ "${SOURCE_REPOSITORY}" = "https://*" ]]; then
  curl --head --silent --fail --location --max-time 16 ${SOURCE_REPOSITORY} > /dev/null
  if [ $? != 0 ]; then
    echo "Could not access source url: ${SOURCE_REPOSITORY}"
    exit 1
  fi
fi

BUILD_DIR=$(mktemp --directory)
git clone --recursive "${SOURCE_REPOSITORY}" "${BUILD_DIR}"
if [ $? != 0 ]; then
  echo "Error trying to fetch git source: ${SOURCE_REPOSITORY}"
  exit 1
fi

pushd "${BUILD_DIR}"

if [ -n "${SOURCE_REF}" ]; then
  git checkout "${SOURCE_REF}"
  if [ $? != 0 ]; then
    echo "Error trying to checkout branch: ${SOURCE_REF}"
    exit 1
  fi
fi

if [ -n "${SOURCE_CONTEXT_DIR}" ]; then
  popd
  pushd "${BUILD_DIR}/${SOURCE_CONTEXT_DIR}"
fi

if [ -n "$TAG" ]; then
  concreate ${CONCREATE_CFG_PATH:+--config="${CONCREATE_CFG_PATH}"} generate
  if [ $? != 0 ]; then
    echo "Error generating Dockerfile with concreate"
    exit 1
  fi

  pushd target/image
  docker build ${TAG:+--tag="${TAG}"} .
  if [ $? != 0 ]; then
    echo "Error building generated Dockerfile"
    exit 1
  fi

  if [ -n "$NO_PUSH" ]; then
    exit 0
  fi

  docker ${PUSH_DOCKERCFG_PATH:+--config="${PUSH_DOCKERCFG_PATH}"} push ${TAG}
  if [ $? != 0 ]; then
    echo "Error pushing image: ${TAG}"
    exit 1
  fi
else
  echo "No image tag specified.  Resulting image will not be pushed to any registry"
  concreate ${CONCREATE_CFG_PATH:+--config="${CONCREATE_CFG_PATH}"} build
  if [ $? != 0 ]; then
    echo "Error building image with concreate"
    exit 1
  fi
fi
