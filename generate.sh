#!/bin/sh

VERSION=${VERSION:="1.0.0"}
INPUT_DIR=${INPUT_DIR:="`pwd`"}
SCRIPTS_DIR=${SCRIPTS_DIR:="$INPUT_DIR/scripts"}
OUTPUT_DIR=${OUTPUT_DIR:="$INPUT_DIR/target"}

# Pre-create the target directory
mkdir -p $OUTPUT_DIR

docker run -t --rm -v $SCRIPTS_DIR:/scripts:z -v $INPUT_DIR:/input:z -v $OUTPUT_DIR:/output:z jboss/dockerfile-generator:$VERSION

