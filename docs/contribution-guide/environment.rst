Setting up environment
=========================

We strongly advise to use `Virtualenv <https://virtualenv.pypa.io/en/stable/>`__ to develop CEKit. Please consult your package manager for the correct package name. Currently within Fedora 29 all the required packages are available as RPMs. A sample set of Ansible scripts that provide all pre-requistites for development are available `here <https://github.com/cekit/cekit/tree/develop/support/ansible>`_.

- If you are running inside the Red Hat infrastructure then ``rhpkg`` must be installed as well.

To create custom Python virtual environment please run following commands on your system:

.. code-block:: bash

    # Prepare virtual environment
    virtualenv ~/cekit
    source ~/cekit/bin/activate

    # Install as development version
    pip install -e <cekit directory>

    # Now you are able to run CEKit
    cekit --help

It is possible to ask virtualenv to inherit pre-installed system packages thereby reducing the virtualenv to a delta between what is installed and what is required. This is achived by using the flag ``--system-site-packages`` (See `here <https://virtualenv.pypa.io/en/latest/userguide/#the-system-site-packages-option>`__ for further information).

.. note::

   Every time you want to use CEKit you must activate CEKit Python virtual environment by executing ``source ~/cekit/bin/activate``

   For those using ZSH a useful addition is `Zsh-Autoswitch-VirtualEnv <https://github.com/MichaelAquilina/zsh-autoswitch-virtualenv>`_ the use of which avoids the labour of manually creating the virtualenv and activating it each time ; simply run ``mkvenv --system-site-packages`` initially and then it is handled automatically then on.
