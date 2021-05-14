#!/bin/sh
set -e

cd /workspace
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GO111MODULE=on go build -a -o rhpam-kogito-operator-manager main.go

