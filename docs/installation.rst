Installation
############
This chapter will guide you through all the steps needed to setup Cekit on your operating system.

.. contents::

Installing Cekit
*****************
We provide RPM packages for Fedora, CentOS, RHEL distribution. Cekit installation on other platforms is still possible via ``pip``

On RHEL derivatives we strongly suggest installing Cekit using the YUM/DNF package manager. We provide a `COPR repository for Cekit <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_
which contains everything needed to install Cekit.

Fedora
------

Supported versions: 27+.

For Fedora we provide custom Copr repository. To enable the repository and install Cekit on your system please run:

.. code-block:: bash

    dnf install dnf-plugin-copr
    dnf copr enable @cekit/cekit
    dnf install python3-cekit

RHEL
----

Supported versions: 7.x

For RHEL we provide custom Copr repository. To enable the repository and install Cekit on your system please run:

.. code-block:: bash

    yum install yum-plugin-copr epel-release
    yum copr enable @cekit/cekit
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
   Every time you want to use Cekit you must activate Cekit Python virtual environment by executing ``source ~/cekit/bin/activate``

Weak requirements
*****************

Cekit uses weak requirements. This means that in order to minimize the dependency tree, Cekit detects at runtime if requirements
to finish the task successfully are met. In case there are missing dependencies, Cekit will exit and let you know about it.

Build
-----

To build container images of the selected type you need to provide following:

* Docker (default)
    * Docker daemon running locally
    * Docker Python bindings
    * `docker-squash library <https://github.com/goldmann/docker-squash>`_
* `Buildah <https://buildah.io/>`_
    * `Buildah <https://github.com/containers/buildah/blob/master/install.md>`_
* `OSBS <https://osbs.readthedocs.io/en/latest/>`_
    * ``fedpkg`` (if running the community version) or ``rhpkg`` (if running Red Hat internal)
    * Valid Kerberos ticket
    * Git

Test
----

:Command: ``test``
:Parameter: None

For running tests you need:

* Docker daemon running locally
* Docker Python bindings
* `Behave <https://github.com/behave/behave>`_
* LXML Python bindings

.. include:: upgrade.rst
