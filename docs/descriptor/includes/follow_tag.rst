Follow Tag
-----------

Key
    ``follow_tag``
Required
    No

Used to denote an image to track the latest version of. This will then be used to replace the floating tag in the
``from`` image with the determined static tag. Only supported with :ref:`redhat configuration
option<handbook/configuration:Red Hat environment>`.

.. code-block:: yaml

    follow_tag: "registry.access.redhat.com/ubi8/ubi-minimal:latest"

