#!/bin/sh

mkdir -p /path/to/application/inside/the/builder
echo "This is an application built in builder image" > /path/to/application/inside/the/builder/image.jar

mkdir -p /path/to
echo "This is a library built in builder image" > /path/to/lib.jar