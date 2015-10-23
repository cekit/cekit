#!/bin/sh

VERSION=${VERSION:="1.0.0"}
echo "Using '$VERSION' version of the generator tool"

TEMPLATE=${TEMPLATE:="`pwd`/image.yaml"}
echo "Using '$TEMPLATE' template"

OUTPUT_DIR=${OUTPUT_DIR:="`pwd`/target"}
echo "Using '$OUTPUT_DIR' as the output directory"

# If SCRIPTS_DIR env variable is not provided,
# check if the default location (currentdir/scripts)
# exists, if yes, assume that this is the scripts
# directory to mount
if [ -z "$SCRIPTS_DIR" ] && [ -d "`pwd`/scripts" ]; then
    SCRIPTS_DIR=${SCRIPTS_DIR:="`pwd`/scripts"}
fi

volumes="-v $TEMPLATE:/input/image.yaml:z -v $OUTPUT_DIR:/output:z"

if [ -n "$SCRIPTS_DIR" ]; then
    echo "Using '$SCRIPTS_DIR' as the scripts directory"
    volumes="$volumes -v $SCRIPTS_DIR:/scripts:z"
fi

# Pre-create the target directory
mkdir -p $OUTPUT_DIR

exec docker run -t --rm $volumes jboss/dogen:$VERSION

