Installation instructions
=========================

.. contents::

We provide RPM packages for Fedora, CentOS, RHEL distribution.
CEKit installation on other platforms is still possible via ``pip``

On RHEL derivatives we strongly suggest installing CEKit using the YUM/DNF package
manager. We provide a `COPR repository for CEKit <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_
which contains everything needed to install CEKit.

.. warning::

   Make sure you read the :doc:`dependencies chapter</installation/dependencies>` of this documentation which contains important
   information about how CEKit dependencies are handled!

Fedora
-------------------

Supported versions: 27+.

For Fedora we provide a custom Copr repository.  To `enable the "cekit" repository <https://docs.pagure.org/copr.copr/how_to_enable_repo.html>`_ and install CEKit on your system, please run:

.. code-block:: bash

    dnf install dnf-plugins-core
    dnf copr enable @cekit/cekit
    dnf install python3-cekit

CentOS / RHEL
-------------------

Supported versions: 7.x

For RHEL / CentOS we provide custom Copr repository. To enable the repository and install
CEKit on your system please run:

.. code-block:: bash

    curl https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/repo/epel-7/group_cekit-cekit-epel-7.repo -o /etc/yum.repos.d/cekit-epel-7.repo
    yum install python2-cekit

Other systems
-------------------

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install CEKit. Please consult your package manager for the correct package name.

To create custom Python virtual environment please run following commands on your system:

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/cekit
    source ~/cekit/bin/activate

    # Install CEKit
    # Execute the same command to upgrade to latest version
    pip install -U cekit

    # Now you are able to run CEKit
    cekit --help

.. note::

   Every time you want to use CEKit you must activate CEKit Python virtual environment by executing ``source ~/cekit/bin/activate``

If you don't want to (or cannot) use Virtualenv, the best idea is to install CEKit in the user's home with the
``--user`` prefix:

.. code-block:: bash

    pip install -U cekit --user

.. .. include:: dependencies.rst

.. .. include:: upgrade.rst

.. .. toctree::
..     :titlesonly:
    
..     dependencies
..     upgrade