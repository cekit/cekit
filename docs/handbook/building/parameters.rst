Common build parameters
================================

Below you can find description of the common parameters that can be added to every build
command.

``--validate``
    Do not generate files nor execute the build but prepare image sources and
    check if these are valid. Useful when you just want to make sure that the
    content is buildable.

    See ``--dry-run``.

``--dry-run``
    Do not execute the build but let's CEKit prepare all required files to
    be able to build the image for selected builder engine. This is very handy
    when you want manually check generated content.

    See ``--validate``.

``--overrides``
    Allows to specify overrides content as a JSON formatted string, directly
    on the command line.

    Example
        .. code-block:: bash

            $ cekit build --overrides '{"from": "fedora:29"}' docker

    Read more about overrides in the :doc:`/handbook/overrides` chapter.

    This parameter can be specified multiple times.

``--overrides-file``
    In case you need to override more things or you just want to save
    the overrides in a file, you can use the ``--overrides-file`` providing the path
    to a YAML-formatted file.

    Example
        .. code-block:: bash

            $ cekit build --overrides-file development-overrides.yaml docker

    Read more about overrides in the :doc:`/handbook/overrides` chapter.

    This parameter can be specified multiple times.
