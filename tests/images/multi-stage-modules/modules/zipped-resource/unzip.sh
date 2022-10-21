#!/bin/bash

set -x

cd /tmp/scripts/zipped-resource
echo $PWD
unzip resource.zip
cp resource.txt /tmp/