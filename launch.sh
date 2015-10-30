#!/bin/sh

set -e

if [ "$#" -lt 2 ]; then
    dogen --help
    exit 1
fi

# Assume that the path to the descriptor file is second from the end
stat=(`stat -c "%u %g" ${@: -2:1}`)

groupadd -r dogen -g ${stat[1]} && useradd -u ${stat[0]} -r -g dogen -M -d /opt/dogen dogen

runuser dogen -c "/usr/bin/dogen $*"

