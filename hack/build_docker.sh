#!/bin/bash

# check if user wants to pass tag
if [[ $# -eq 0 ]] ; then
   dogen_tag=""
else
   dogen_tag=":$1"
fi

DOGEN_REPO=$(dirname $0)/..

tar --exclude hack -cf $DOGEN_REPO/hack/dogen.tar  -C $DOGEN_REPO .

docker build -t jboss/dogen$dogen_tag hack/

rm $DOGEN_REPO/hack/dogen.tar

