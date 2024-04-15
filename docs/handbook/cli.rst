CLI Tooling
===========

The ``cekit`` CLI tool supports the following common options:

``--descriptor``
    The path to the image descriptor file. It defaults to ``image.yaml``. If ``-`` is passed in it will read from
    standard input.

``-v`` ``--verbose``
    Enable verbose logging

``--trace``
    Enable trace logging

``--nocolor``
    Disable color output. This is also implicitly activated when the environment variable ``NO_COLOR`` is set.

``--work-dir PATH``
    Location of the working directory. Defaults to ``$HOME/.cekit``.

``--config PATH``
    Path to the configuration file. See :doc:`/handbook/configuration`

``--redhat``
    Enables options for Red Hat infrastructure. See  :doc:`/handbook/redhat`

``--target PATH``
    Path to directory where files should be generated. Defaults to ``target``

``--version``
    Outputs CEKit version and exits

``--help``
    Outputs help information and exits
