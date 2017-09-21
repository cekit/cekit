Installation
============

Fedora / CentOS / RHEL
-----------------------

We suggest installing Concreate using the YUM/DNF package manager. We provide a `COPR repository for Concreate <https://copr.fedorainfracloud.org/coprs/goldmann/concreate/>`_
which contains everything needed to install Concreate.

Fedora
^^^^^^^

Supported versions: 25, 26, 27.

.. code-block:: bash

    dnf copr enable goldmann/concreate
    dnf install python3-concreate

CentOS / RHEL
^^^^^^^^^^^^^

Supported versions: 7.

.. code-block:: bash

    yum install yum-plugin-copr
    yum copr enable goldmann/concreate
    yum install python2-concreate

Other systems
--------------

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Concreate. Please consult
your package namager of choice for the correct package name.

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/concreate
    source ~/concreate/bin/activate

    # Install Concreate
    # Execute the same command to upgrade to latest version
    pip install -U concreate

    # Now you are able to run Concreate
    concreate --help

Requirements
^^^^^^^^^^^^^

To build container images you need to have Docker installed on your system.
