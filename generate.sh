#!/bin/sh

VERSION=${VERSION:="1.0.0"}
TEMPLATE=${TEMPLATE:="`pwd`/image.yaml"}
SCRIPTS_DIR=${SCRIPTS_DIR:="`pwd`/scripts"}
OUTPUT_DIR=${OUTPUT_DIR:="`pwd`/target"}

# Pre-create the target directory
mkdir -p $OUTPUT_DIR

echo "Using template: $TEMPLATE"
echo "Using scripts directory: $SCRIPTS_DIR"
echo "Using output directory: $OUTPUT_DIR"

exec docker run -it --rm -v $SCRIPTS_DIR:/scripts:z -v $TEMPLATE:/input/image.yaml:z -v $OUTPUT_DIR:/output:z jboss/dockerfile-generator:$VERSION

