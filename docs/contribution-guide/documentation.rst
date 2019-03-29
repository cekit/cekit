Contributing to documentation
===============================

We use the `reStructuredText <http://docutils.sourceforge.net/rst.html>`_ format to
write our documentation because this is the de-facto standard for Python documentation.
We use `Sphinx <http://www.sphinx-doc.org/en/stable/index.html>`_ tool to generate documentation
from reStructuredText files.

Published documentation lives on Read the Docs: `<https://cekit.readthedocs.io/>`_

reStructuredText
-------------------

A good guide to this format is available in the `Sphinx documentation <http://www.sphinx-doc.org/en/stable/rest.html>`_.

Local development
---------------------

.. note::

    The documentation has its own ``requirements.txt``. As above we would recommend using
    `Virtualenv <https://virtualenv.pypa.io/en/stable/>`_ to use a clean development environment.
    The Ansible scripts above will install all documentation pre-requisites as well.

Support for auto generating documentation is avialable for local development. Run the command below.

.. code-block:: bash

    make preview

Afterwards you can see generated documentation at `<http://127.0.0.1:8000>`_. When you edit any file,
documentation will be regenerated and immediately available in your browser.

Guidelines
-------------

Below you can find a list of conventions used to write CEKit documentation. Reference information on reStructuredText
may be found `here <http://docutils.sourceforge.net/rst.html>`__.

Headers
^^^^^^^

Because reStructredText does not enforce what characters are used to mark header
to be a certain level, we use following guidelines:

.. code-block:: rst

    h1 header
    =========

    h2 header
    ---------

    h3 header
    ^^^^^^^^^

    h4 header
    *********
