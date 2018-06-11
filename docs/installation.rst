Installation
############
This chapter will guide you through all the steps needed to setup Cekit on your operating system.

.. contents::

Installing Cekit
*****************
We provide RPM packages for Fedora, CentOS, RHEL distribution. Cekit installation on other platforms is still possible via `pip`

Fedora / CentOS / RHEL
----------------------

On RHEL derivatives we strongly suggest installing Cekit using the YUM/DNF package manager. We provide a `COPR repository for Cekit <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_
which contains everything needed to install Cekit.

Fedora
^^^^^^

Supported versions: 27, 28.

For Fedora we provide custom Copr repository. To enable the repository and install Cekit on your system please run:

.. code-block:: bash

    yum install yum-plugin-copr
    yum copr enable @cekit/cekit
    yum install python2-cekit

RHEL
^^^^

Supported versions: 7.x

For RHEL we provide custom Copr repository. To enable the repository and install Cekit on your system please run:

.. code-block:: bash

    curl https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/repo/epel-7/group_cekit-cekit-epel-7.repo -o /etc/yum.repos.d/cekit-epel-7.repo
    yum install python2-cekit

Other systems
-------------

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Cekit. Please consult your package manager for the correct package name.

To create custom Python virtual environment please run following commands on your system:

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/cekit
    source ~/cekit/bin/activate

    # Install Cekit
    # Execute the same command to upgrade to latest version
    pip install -U cekit

    # Now you are able to run Cekit
    cekit --help

.. note::
   Every time you want to use Cekit you must activate Cekit Python virtual environment by executing `source ~/cekit/bin/activate`

Requirements
============

Build
-----
To build container images you need one of the following:

* docker
* buildah

Test
----
For running tests you need:

* docker
* docker python bindings
* behave
* python-lxml

.. include:: upgrade.rst
