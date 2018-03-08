Installation
============

Fedora / CentOS / RHEL
-----------------------

We suggest installing Cekit using the YUM/DNF package manager. We provide a `COPR repository for Cekit <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_
which contains everything needed to install Cekit.

Fedora
^^^^^^^

Supported versions: 25, 26, 27.

.. code-block:: bash

    dnf copr enable @cekit/cekit
    dnf install python3-cekit

CentOS
^^^^^^

Supported versions: 7.

.. code-block:: bash

    yum install yum-plugin-copr
    yum copr enable @cekit/cekit
    yum install python2-cekit

RHEL
^^^^^^

Supported versions: 7.

.. code-block:: bash

    curl https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/repo/epel-7/group_cekit-cekit-epel-7.repo -o /etc/yum.repos.d/cekit-epel-7.repo
    yum install python2-cekit

Other systems
--------------

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Cekit. Please consult
your package manager of choice for the correct package name.

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/cekit
    source ~/cekit/bin/activate

    # Install Cekit
    # Execute the same command to upgrade to latest version
    pip install -U cekit

    # Now you are able to run Cekit
    cekit --help

Requirements
------------

Build
^^^^^
To build container images you need:

* Docker

Test
^^^^
For running tests you need:

* docker python bindings
* behave
* python lxml
