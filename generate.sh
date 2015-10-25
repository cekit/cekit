#!/bin/sh

# Helper script to run the jboss/dogen tool
# 
# Honored environment variables. All variables are optional.
#
# - TEMPLATE:       defaults to $PWD/image.yaml, path the the template
#                   (image.yaml) file, fails if the file does not exists
#
# - OUTPUT_DIR:     defaults to $PWD/target, target directory, creates
#                   the target directory if necessary
#
# - SCRIPTS_DIR:    defaults to $PWD/scripts, path to scripts directory,
#                   fails if the directory does not exists, if the environment
#                   variable is not provided checks if $PWD/scripts directory
#                   exists and uses this directory
#
# - VERSION:        defaults to latest stable release, version of the tool to run
#
# ------------------------------------------------------------

VERSION=${VERSION:="1.0.0"}

if [ -n "$TEMPLATE" ] && [ ! -f "$TEMPLATE" ]; then
    echo "Cannot find '$TEMPLATE' template, make sure the file exists, aborting."
    exit 1
fi

if [ -z "$TEMPLATE" ] && [ -f "$PWD/image.yaml" ]; then
    TEMPLATE="$PWD/image.yaml"
else
    echo "Cannot find image.yaml template in the current directory nor 'TEMPLATE' env variable was set, aborting."
    exit 1
fi

if [ -n "$SCRIPTS_DIR" ] && [ ! -d "$SCRIPTS_DIR" ]; then
    echo "Cannot find '$SCRIPTS_DIR' directory, make sure you provided correct path to scripts directory, aborting."
    exit 1
fi

# If SCRIPTS_DIR env variable is not provided,
# check if the default location ($PWD/scripts)
# exists, if yes, assume that this is the scripts
# directory to mount
if [ -z "$SCRIPTS_DIR" ] && [ -d "$PWD/scripts" ]; then
    SCRIPTS_DIR="$PWD/scripts"
fi

# If the directory that contains the template is a git repository
# get the last commit ID and store it in the SOURCE_COMMIT_ID
# environment variable. This could be used later in the dogen
# tool for example in the commit message when used with
# DIST_GIT env variable set to true
pushd `dirname $TEMPLATE` > /dev/null
    commit=$(git rev-parse HEAD 2> /dev/null)
    if [ "$?" = "0" ]; then
        export SOURCE_COMMIT_ID=$commit
    fi
popd > /dev/null

OUTPUT_DIR=${OUTPUT_DIR:="$PWD/target"}

echo "Using '$VERSION' version of the generator tool"
echo "Using '$TEMPLATE' template"
echo "Using '$OUTPUT_DIR' as the output directory"

# Pre-create the target directory
mkdir -p $OUTPUT_DIR

cmd="/input/image.yaml /output"
volumes="-v $TEMPLATE:/input/image.yaml:z -v $OUTPUT_DIR:/output:z"

if [ -n "$SCRIPTS_DIR" ]; then
    echo "Using '$SCRIPTS_DIR' as the scripts directory"
    volumes="$volumes -v $SCRIPTS_DIR:/scripts:z"
    cmd="--scripts /scripts $cmd"
fi

if [ -n "$DIST_GIT" ]; then
    cmd="--dist-git $cmd"
fi

exec docker run -t --rm $volumes ce-registry.usersys.redhat.com/jboss/dogen:$VERSION $cmd
