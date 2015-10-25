Dockerfile generator
====================

This is a simple tool to generate `Dockerfile` files from YAML templates.


.. image:: http://i.imgur.com/o7pzVYb.jpg
   :width: 400 px

Usage
-----

This tool is shipped as a Docker image registered as :code:`jboss/dogen`.
You can see the :code:`Dockerfile` for this image in the main directory
of the source distribution. This Docker image uses some conventions:

1. The image template that should be converted into :code:`Dockerfile` is expected to be
   available at :code:`/input/image.yaml`.
2. The output directory will be :code:`/output`.
3. The directory with (optional) scripts should be available at :code:`/scripts`.

Considering above you need to remember to mount appropriate volumes at the container
start. You are free to change the paths, but please remember to provide new locations
as part of the container's :code:`run` command instruction.

::

    $ docker run -it --rm jboss/dogen:1.0.0 --help
    usage: dogen [-h] [-v] [--version] [--without-sources] [--dist-git]
                 [--scripts SCRIPTS]
                 template output
    
    Dockerfile generator tool
    
    positional arguments:
      template              Path to yaml template to process
      output                Path to directory where generated files should be
                            saved
    
    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         Verbose output
      --version             Show version and exit
      --without-sources, --ws
                            Do not process sources, only generate Dockerfile
      --dist-git            Specifies if the target directory is a dist-git
                            repository
      --scripts SCRIPTS     Location of the scripts directory

Example
~~~~~~~

::

For image without scripts to be added::

    docker run -it --rm -v PATH_TO_IMAGE_YAML:/input/image.yaml:z -v PATH_TO_TARGET_DIR:/output:z jboss/dogen:1.0.0

For image with scripts to be added::

    docker run -it --rm -v PATH_TO_SCRIPTS_DIR:/scripts:z -v PATH_TO_IMAGE_YAML:/input/image.yaml:z -v PATH_TO_TARGET_DIR:/output:z jboss/dogen:1.0.0