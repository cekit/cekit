#!/bin/sh

set -x

SCRIPT_DIR=$(dirname $0)

echo "Installing application..."

cp /tmp/artifacts/application /root/
cp /tmp/artifacts/lib.jar /root/

cat /root/application
cat /root/lib.jar