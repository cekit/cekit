Upgrading Cekit
===============

Fedora / CentOS / RHEL
-----------------------
On this platform you should be using RPM and our `COPR repository for Cekit <https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/>`_

*Note*: We assume, that you have this repository enabled on your system

Fedora
^^^^^^^
Supported versions: 25, 26, 27.

.. code-block:: bash

    dnf update python3-cekit

CentOS & RHEL
^^^^^^^^^^^^^

Supported versions: 7.

.. code-block:: bash

    yum update python2-cekit


Other systems:
-------------
We suggest using pip and `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to host you Cekit.

.. code-block:: bash

    # Activate virtual environment
    source ~/cekit/bin/activate

    pip install -U cekit


Upgrading from Concreate
========================

Cekit and Concreate are the very same tool. Concreate was rename to Cekit in 2.0 release.

Fedora / CentOS / RHEL
----------------------
You should be using RPM and yum/dnf to manage Cekit/Concreate installation here.

Fedora
^^^^^^

Supported versions: 25, 26, 27.

.. code-block:: bash

    dnf remove python3-concreate
    dnf copr remove goldmann/concreate

    dnf copr enable @cekit/cekit
    dnf install python3-cekit

CentOS
^^^^^^

Supported versions: 7.

.. code-block:: bash

    yum remove python2-concreate
    rm -rf  /etc/yum.repos.d/_copr_goldmann-concreate.repo
    
    yum copr enable @cekit/cekit
    yum install python2-cekit

RHEL
^^^^

 Supported versions: 7.

.. code-block:: bash

    yum remove python2-concreate
    rm -rf /etc/yum.repos.d/goldmann-concreate-epel-7.repo

    curl https://copr.fedorainfracloud.org/coprs/g/cekit/cekit/repo/epel-7/group_cekit-cekit-epel-7.repo -o /etc/yum.repos.d/cekit-epel-7.repo
    yum install python2-cekit


Other systems
-------------

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to install Cekit. Please consult
your package manager of choice for the correct package name.

.. code-block:: bash

    # Activate virtual environment
    source ~/cekit/bin/activate

    pip uninstall concreate
    pip install -U cekit


Dotfile migration
-----------------

Concreate used *~/.concreate.d* and *~/.concreate* dot files to held its configuration. This was changed with Cekit.
Cekit uses only *~/.cekit* directory to host all its configuration files.

To migrate your configuration please run:

.. code-block:: bash

    mv ~/.concreate.d ~/.cekit
    mv ~/.concreate ~/.cekit/config
