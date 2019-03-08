Global options
==============

There are various options which apply to both `building <build.html>`_ and `testing <testing>`_ options. These are:

* ``--descriptor`` -- Path to image descriptor file. Defaults to ``image.yaml``
* ``-v, --verbose`` -- Enable verbose output.
* ``--work-dir`` -- sets CEKit working directory. Defaults to ``~/.cekit``.  See :ref:`Configuration section for work_dir<workdir_config>`
* ``--config`` -- Path to configuration file. Defaults to ``~/.cekit/config``
* ``--redhat`` -- Set default options for Red Hat internal infrastructure. See :ref:`Configuration section for Red Hat specific options<redhat_env>` for additional details.
* ``--target`` -- Path to directory where files should be generated. Defaults to ``target``
* ``--package-manager`` -- allows selecting between different package managers such as ``yum`` or ``microdnf``. Defaults to ``yum`` *Deprecated option*
* ``--version`` -- Show the version and exit.
* ``--help`` -- Show this message and exit.
