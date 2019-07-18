Module naming
===================

.. contents::
    :backlinks: none

In this section we will be talking about about best practices related to module naming.

Suggested naming scheme
------------------------------

We suggest to use `reverse domain convention <https://en.wikipedia.org/wiki/Reverse_domain_name_notation>`__:

.. code-block:: yaml

    name: "org.jboss.container.openjdk"
    version: "11"
    description: "OpenJDK 11 module"

    # [SNIP]

We suggest to use **lower-case letters**.

Background
^^^^^^^^^^^^

This approach is used in many languages (like Java, or C#) to define modules/packages. Besides this
`it is suggested to be used in defining container image label names <https://docs.docker.com/config/labels-custom-metadata/#key-format-recommendations>`__.

There are a few reasons why it is so popular and a great choice for module names too:

1.  Simplicity.
2.  Module maintainer is known immediately by looking just at the name.
3.  Module name clashes are unlikely.

