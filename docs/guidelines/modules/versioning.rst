Module versioning
===================

.. contents::
    :backlinks: none

This section focuses on best practices around module versioning. For information about how module
versions are handled in CEKit take a look at :doc:`descriptor documentation for modules </handbook/modules/versioning>`.

Suggested versioning scheme
------------------------------

You are free to define your versioning scheme, but we strongly suggest to follow `Python versioning scheme <https://www.python.org/dev/peps/pep-0440/>`__.

.. code-block::

    MAJOR.MINOR.MICRO

Although it was developed for Python - it's easy to reuse it anywhere, including modules versioning.

.. note::
    Its design is very similar to `semantic versioning scheme <https://semver.org/>`__. You can read
    about differences between these two `here <https://www.python.org/dev/peps/pep-0440/#semantic-versioning>`__.

Versioning summary
^^^^^^^^^^^^^^^^^^^^^^

1.  Use ``MAJOR.MINOR.MICRO`` versioning scheme.
2.  Try to **avoid release suffixes**, but if you really need to add one of them, use
    PEP 440 style:

    *   `Pre-releases <https://www.python.org/dev/peps/pep-0440/#pre-releases>`__ like Alpha, Beta, Release Candidate

        .. note::
            There is no dot before the modifier.

        .. code-block::

            MAJOR.MINORaN   # Alpha release:        1.0a1
            MAJOR.MINORbN   # Beta release:         1.0b1
            MAJOR.MINORrcN  # Release Candidate:    1.0rc1
            MAJOR.MINOR     # Final release:        1.0

    *   `Post-releases <https://www.python.org/dev/peps/pep-0440/#post-releases>`__

        .. note::
            Please note the dot before the ``post`` modifier.

        .. code-block::

            MAJOR.MINOR.postN   # Post-release:     1.0.post1

    *   `Development releases <https://www.python.org/dev/peps/pep-0440/#developmental-releases>`__

        .. note::
            Please note the dot before the ``dev`` modifier.

        .. code-block::

            MAJOR.MINORaN.devM       # Developmental release of an alpha release:       1.0a1.dev1
            MAJOR.MINORbN.devM       # Developmental release of a beta release:         1.0b1.dev1
            MAJOR.MINORrcN.devM      # Developmental release of a release candidate:    1.0rc1.dev1
            MAJOR.MINOR.postN.devM   # Developmental release of a post-release:         1.0.post1.dev1

Custom versioning scheme
---------------------------

Although it is possible to to use a custom versioning scheme for modules, we suggest to not use it.
Custom versioning scheme can lead to issues that will be hard to debug, especially when
your image uses multiple module repositories and many modules.

You should be fine when you will be strictly defining modules and versions in the image descriptor,
but it's very problematic to do so. It's even close to impossible when you do not control
the modules you are consuming.

As an example, an issue can arrive when you mix versioning schemes in modules. Version that follows
the :ref:`suggested versioning scheme <guidelines/modules/versioning:Suggested versioning scheme>` will
always take precedence before a custom versioning scheme.

.. seealso::
    See information about :ref:`parsing module versions <handbook/modules/versioning:Parsing>`.

Changelog
---------------------------

Just as any other library, a module should carry a changelog. Every release should have published list
of changes made in the code. This will make it much easier to consume particular module.
