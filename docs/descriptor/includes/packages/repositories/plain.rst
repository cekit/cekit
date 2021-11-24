Plain repository
*******************

.. note::
    Available only on RPM-based distributions.

With this approach you specify repository ``id`` and CEKit will not perform any action
and expect the repository definition exists inside the image. This is useful as a hint which
repository must be present for particular image to be buildable. The definition can be overridden
by your preferred way of injecting repositories inside the image.

.. code-block:: yaml

    packages:
        repositories:
            - name: extras
              id: rhel7-extras-rpm
              description: "Repository containing extras RHEL7 extras packages"
