Description
-------------

Key
    ``description``
Required
    No

Short summary of the image.

Value of the ``description`` key is added to the image as two labels:

1. ``description``, and
2. ``summary``.

.. note::
    These labels are not added is these are already defined in the `labels <#labels>`__ section.

.. code-block:: yaml

    description: "Red Hat JBoss Enterprise Application 7.0 - An application platform for hosting your apps that provides an innovative modular, cloud-ready architecture, powerful management and automation, and world class developer productivity."
