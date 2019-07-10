Module versioning
===================

.. contents::
    :backlinks: none

Module versioning is an important aspect of image development process. Proper handling of versions makes it easy
to control what exactly content should be part of the image.

This section describes how module versions are handled in CEKit.

.. seealso::
    If you want to learn best practices around module versioning, take a look at :doc:`module guidelines </guidelines/modules/versioning>`.

Requirements
------------------

Every module **must have a version defined**. Version of the module is an important piece of information
because based on the version we control what content goes into image.

You can look at module versioning similar to any library version. There are no libraries without version
and there must not be modules without versions.

In module descriptor the version could be defined as string, float or integer. CEKit is converting this
value internally to string which is :ref:`parsed later <handbook/modules/versioning:Parsing>` to
become a version object finally.

.. note::

    Although CEKit does not enforce any versioning scheme, se suggest to use Python versioning scheme.
    Read more about :ref:`suggested approach <guidelines/modules/versioning:Suggested versioning scheme>`.

    If your module version does not follow this scheme, CEKit will **log a warning**. In case you use
    your :ref:`own versioning scheme <guidelines/modules/versioning:Custom versioning scheme>` you
    can ignore this warning.

Parsing
------------------------------------

Every version of module is parsed internally. Before we can do this **any version is converted to string**.
This means that

.. code-block:: yaml

    version: 1.0

and

.. code-block:: yaml

    version: "1.0"

are **exactly the same versions** for CEKit.

Handling modules with multiple versions
-----------------------------------------

.. seealso::
    See :doc:`module descriptor documentation </descriptor/module>` and :ref:`image descriptor modules section documentation <descriptor/image:Modules>`
    for more information how to reference modules.

In case you do not specify version requirement in the module installation list in the image descriptor,
CEKit will use **newest version to install**.

Internally we use the `packaging module <https://packaging.pypa.io/en/latest/>`__ to convert the module version
string into a `Version <https://packaging.pypa.io/en/latest/version/#packaging.version.Version>`__ object.
If you use a :ref:`custom versioning scheme <guidelines/modules/versioning:Custom versioning scheme>`
your version may be represented by a `LegacyVersion <https://packaging.pypa.io/en/latest/version/#packaging.version.LegacyVersion>`__ object.

Parsed versions are compared according to `PEP 440 <https://www.python.org/dev/peps/pep-0440/>`__ versioning scheme.

:ref:`Custom versioning scheme <guidelines/modules/versioning:Custom versioning scheme>` in comparison with a PEP 440
version will be **always older**.
