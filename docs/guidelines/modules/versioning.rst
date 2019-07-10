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

Git references vs. module versions
-----------------------------------

It is very common use case to place modules inside a Git repository. This is a very efficient
way to share modules with others.

Git repositories are always using version of some sort, in Git we talk about ref's. This can be
a branch or a tag name. References can point to a stable release (tags) or to a work in progress
(branches).

:ref:`Defining module version is required <handbook/modules/versioning:Requirements>` in CEKit.
This means that the module definition must have the ``version`` key.

If you reference modules stored in a Git repository we can talk about two layers of versioning:

1. Git references
2. Module versions itself

We will use a simple example to explain how we can reference modules. Here is the module descriptor.

.. code-block:: yaml
   :caption: module.yaml

    name: "org.company.project.feature"
    version: "1.0"

    execute:
        - script: "install.sh"

Below you can see the image descriptor snippet with only relevant content for this example.

.. code-block:: yaml
   :caption: image.yaml

    modules:
        repositories:
            - name: "org.company.project"
              git:
                url: "https://github.com/company/project-modules"
                ref: "release-3.1.0"

        install:
            - name: "org.company.project.feature"

.. note::
    As you can see above, the module repository does have a different reference than ``1.0``.
    This is not a mistake - module repositories can contain multiple modules with different
    versions. Module repositories **group modules** together under a **single version**.

Referencing stable versions of modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Referencing stable versions of modules is very easy. The most important thing to remember
is that in order to pin a version of module, we need to be able to
**pin to a specific version of the module registry itself too**.

Referencing tags is a great way to ensure that we use the same code always.
This means that the git repository references need to be managed carefully and proper
tag management need to be preserved (no force push on tags).

Once we have tags -- we can reference them in the module registry ``ref`` just like
in the example above.

We don't need to specify versions in the install section of modules as long as we have a single
version of particular module available in repositories. If this is not the case and in
your workflow you maintain multiple versions of same module -- specifying version to install
may be required.

.. note::

    An example could be a module that installs OpenJDK 8 and OpenJDK 11 -- name of the module
    is the same, these live in the same module repository, but versions differ.

If multiple versions of a particular module are available and the version will not be specified
in the module installation section
:ref:`newest version will be installed <handbook/modules/versioning:Handling modules with multiple versions>`.

Referencing development versions of modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Module being currently in development should have set the version in module descriptor being the
next (target) version. This will make sure the version is already set in the module and no
code changes are required to actually *release* a module.

Assuming that the current released version of the module is ``1.0``, we can develop the ``2.0``
version of this module, so we just define it in the module descriptor:

.. code-block:: yaml
   :caption: module.yaml

    name: "org.company.project.feature"
    version: "2.0"

    execute:
        - script: "install.sh"

If we develop module locally and reference the module repository using ``path`` attribute,
no Git repository references are used at all. Modules are copied from the repository to the
target directory and used there at build time.

We can use :doc:`overrides feature </handbook/overrides>` to point to our development work.
Using overrides makes it easy to not touch the image descriptor at development time.

.. code-block:: yaml
   :caption: overrides.yaml

    modules:
        repositories:

            # Override our module repository location to point to a local directory
            - name: "org.company.project"
              path: "project-modules"

Please note that we did not specify which version of the ``org.company.project.feature`` module
should be installed. This is perfectly fine! Since we are overriding the module repository,
the only module version of the ``org.company.project.feature`` available will be our
locally developed -- ``2.0``, so there is no need to define it, but of course we can do it.

If we want to share with someone our development work, we should push the module repository
to a Git repository **using specific branch**. This branch could be a feature branch,
or a regular development branch (for example ``master``), it depends on your workflow.

In our example, let's use a feature branch: ``feature-dev``. Once code is pushed to this
branch, we can update our ``overrides.yaml`` file to use it:

.. code-block:: yaml
   :caption: overrides.yaml

    modules:
        repositories:
            - name: "org.company.project"
              git:
                url: "https://github.com/company/project-modules"
                ref: "feature-dev"





Changelog
---------------------------

Just as any other library, a module should carry a changelog. Every release should have published list
of changes made in the code. This will make it much easier to consume particular module.
