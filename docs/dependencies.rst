Dependencies
============

By default when you install Cekit, **only required core dependencies are installed**.
This means that in order to use some generators or builders you may need to install
additional software.

Building container images for various platforms requires many dependencies to be present.
We don't want to force installation of unnecessary utilities thus we decided to limit
dependencies to the bare minimum.

If a required dependency (for particular run) is not satisfied, user will be let know
about the fact. In case of known platforms (like Fedora or RHEL) we even provide the
package names to install (if available).

Below you can see a summary of Cekit dependencies and when these are required.

Core dependencies
----------------------------------

Following Python libraries are required to run Cekit:

* PyYAML
* Jinja2
* pykwalify
* colorlog

Additionally, we require Git to be present since we use it in many places.

For more information, please consult the ``Pipfile`` file available in the Cekit repository.

Generate phase dependencies
----------------------------------

* ``odcs-client`` package
    This is required when ``generate`` command and ``--build-engine buildah`` or ``--build-engine docker``
    parameters are used. This package is available for Fedora and the CentOS family in the EPEL repository.


Build phase dependencies
----------------------------------

* Docker
    This is required when ``build`` command and ``--build-engine docker`` parameter is used.
    This is the default builder engine.

* `Buildah <https://buildah.io/>`_
    This is required when ``build`` command and ``--build-engine buildah`` parameter is used.

* ``fedpkg`` package
    This is required when ``build`` command and ``--build-engine osbs`` parameter is used.

* ``rhpkg`` package
    This is required when ``build`` command and ``--build-engine osbs``  and ``--redhat`` parameters are used.

* ``rhpkg-stage`` package
    This is required when ``build`` command and ``--build-engine osbs``  and ``--redhat`` and ``--stage`` parameters are used.


Test phase dependencies
----------------------------------

For more information about testing, please take a :doc:`look here </test>`.

Test dependencies can vary. Cekit uses a plugable way of defining Behave steps. The default
test steps are located in https://github.com/cekit/behave-test-steps repository. You can find there
more information about the current dependencies.