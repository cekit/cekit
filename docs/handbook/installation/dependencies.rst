Dependencies
============

By default when you install CEKit, **only required core dependencies are installed**.
This means that in order to use some generators or builders you may need to install
additional software.

Building container images for various platforms requires many dependencies to be present.
We don't want to force installation of unnecessary utilities thus we decided to limit
dependencies to the bare minimum (core dependencies).

If a required dependency (for particular run) is not satisfied, user will be let know
about the fact. In case of known platforms (like Fedora or RHEL) we even provide the
package names to install (if available).

Below you can see a summary of CEKit dependencies and when these are required.

.. contents::
    :backlinks: none

Core dependencies
----------------------------------

Following Python libraries are required to run CEKit:

* PyYAML
* Jinja2
* pykwalify
* colorlog
* click

.. note::
    For more information about versions, please consult the ``Pipfile`` file available in the `CEKit repository <https://github.com/cekit/cekit/>`__.

Additionally, we require **Git** to be present since we use it in many places.

Builder specific dependencies
----------------------------------

This section describes builder-specific dependencies.

Docker builder dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Docker
    Required to build the image.
`Docker Python bindings <https://github.com/docker/docker-py>`__
    We use Python library to communicate with the Docker daemon instead of using the ``docker`` command directly.
    Both, old (``docker-py``) and new (``docker``) library is supported.
`Docker squash tool <https://github.com/goldmann/docker-squash>`__
    After an image is built, all layers added by the image build process are squashed together with this tool.

    .. note::
        We are aware that Docker now supports the ``--squash`` parameter, but it's still an experimental
        feature which requires reconfiguring the Docker daemon to make it available. By default it's
        disabled. Instead relying on this, we use a proven tool that works in any case.


.. _redhat_docker_builder_requirements:

.. important::
    If run within the :doc:`Red Hat environment</handbook/redhat>` additional dependencies are required.

    ``odcs`` command
        This is required when ``generate`` command and ``--build-engine buildah`` or ``--build-engine docker``
        parameters are used. This package is available for Fedora and the CentOS family in the EPEL repository.
        For RHEL/Fedora OS'es this is satisfied by installing the ``odcs-client`` package.
    ``brew`` command
        Used to identify and fetch artifacts from Brew.

Buildah builder dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Buildah <https://buildah.io/>`__
    Required to build the image.

.. important::
    If run within the :doc:`Red Hat environment</handbook/redhat>` additional dependencies are required. See the
    :ref:`note in the Docker section above<redhat_docker_builder_requirements>` for more details.

Podman builder dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* `Podman <https://podman.io/>`__
    Required to build the image.

.. important::
    If run within the :doc:`Red Hat environment</handbook/redhat>` additional dependencies are required. See the
    :ref:`note in the Docker section above<redhat_docker_builder_requirements>` for more details.

OSBS builder dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``koji`` command
    The ``koji`` command is used to interact with the Koji API to execute the build.
``fedpkg`` command
    Used to clone and interact with dist-git repositories.

.. important::
    If run within the :doc:`Red Hat environment</handbook/redhat>` above dependencies are replaced with
    Red Hat specific tools:

    * ``koji`` is replaced by ``brew`` command (or ``brew-stage`` if run with the ``--stage`` parameter)
    * ``fedpkg`` is replaced by ``rhpkg`` command (or ``rhpkg-stage`` if run with the ``--stage`` parameter)

Test phase dependencies
----------------------------------

For more information about testing, please take a :doc:`look here </handbook/testing/index>`.

Test dependencies can vary. CEKit uses a plugable way of defining Behave steps. The default
test steps are located in https://github.com/cekit/behave-test-steps repository. You can find there
more information about the current dependencies.


Development dependencies
-----------------------------
If you wish to contribute and develop CEKit itself (including running CEKit tests) then please see :doc:`Contributing</contribution-guide/environment>`
