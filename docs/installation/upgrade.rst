Upgrading
=========

.. note::

    If you run on Fedora / CentOS / RHEL you should be using RPMs
    from regular repositories. Please see :doc:`installation instructions </installation/instructions>`.

Upgrade from CEKit 2.x
-----------------------

Previous CEKit releases were provided via the `COPR repository <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_
which is now **deprecated**. The COPR repository **won't be updated anymore** with new releases.

Fedora packages are not compatible with packages that come from the
`deprecated COPR repository <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_,
you need to uninstall any packages that came from it before upgrading.

.. tip::
    You can use ``dnf repolist`` to get the repository id (should be ``group_cekit-cekit`` by default)
    which can be used for querying installed packages and removing them:

    .. code-block:: bash

        dnf list installed | grep @group_cekit-cekit | cut -f 1 -d ' ' | xargs sudo dnf remove {}\;

Once all packages that came from the COPR repository you can follow the :doc:`installation instructions </installation/instructions>`.

Fedora
--------------------

.. code-block:: bash

    dnf update cekit

CentOS / RHEL
--------------------

.. code-block:: bash

    yum update cekit


Other systems
-------------

Use the ``pip -U`` switch to upgrade the installed module.

.. code-block:: bash

    pip install -U cekit --user
