Package manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key
    ``manager``
Required
    No

It is possible to define package manager used in the image
used to install packages as part of the build process.

Currently available options are ``yum``, ``dnf``, ``microdnf``, ``apt-get`` and ``apk``.

.. note::
    If you do not specify this key the default value is ``yum``.
    If your image requires different package manager you need to specify it.

    It is only possible to define a single package manager for an image (although multi-stage images may have
    different package managers). A package manager may be defined in a module or in an image (the latter takes
    precedence).

    The default ``yum`` value will work fine on Fedora and RHEL images because
    OS maintains a symlink to the proper package manager.

.. note::
    For ``yum``, ``dnf`` and ``microdnf`` the flag ``--setopt=tsflags=nodocs`` is automatically added. For ``microdnf``, the flag ``--setopt=install_weak_deps=0`` is also added.

.. note::
    For ``apt-get`` the flag ``--no-install-recommends`` is also added.

.. code-block:: yaml

    packages:
        manager: dnf
        install:
            - git


Package manager flags
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is an optional key. It is only needed to **override** the default package manager flag values. For example, with a
package manager of ``microdnf``. the default flags are ``--setopt=tsflags=nodocs --setopt=install_weak_deps=0``.

.. code-block:: yaml

    packages:
        manager: microdnf
        manager_flags:

This will override the flags meaning that *no* flags are passed to ``microdnf``.


.. code-block:: yaml

    packages:
        manager: microdnf
        manager_flags: --setopt=tsflags=nodocs

This will also override the flags but only add the single option which is useful for older ``microdnf``
versions (pre 3.4.0) which do not support extended ``setopt`` commands.
