#!/bin/sh

set -e

if [ "$#" -lt 2 ]; then
    dogen --help
    exit 1
fi

# Assume that the path to the descriptor file is second from the end
stat=(`stat -c "%g %u" ${@: -2:1}`)

if [ "${stat[0]}" != "0" ] && [ "${stat[1]}" != "0" ]; then
    groupadd -r dogen -g ${stat[0]}
    useradd -u ${stat[1]} -r -g dogen -M -d /opt/dogen dogen
    runuser dogen -c "/usr/bin/dogen $*"
else
    /usr/bin/dogen "$@"
fi


