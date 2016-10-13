#!/bin/bash

set -e

if [ "$#" -lt 2 ]; then
    dogen --help
    exit 1
fi

# Assume that the path to the descriptor file is second from the end
stat=(`stat -c "%g %u" ${@: -2:1}`)

if [ "${stat[0]}" != "0" ] && [ "${stat[1]}" != "0" ]; then
    addgroup -S -g ${stat[0]} dogen
    adduser -u ${stat[1]} -S -G dogen dogen
    sudo -E -u dogen /usr/bin/dogen $*
else
    /usr/bin/dogen "$@"
fi


