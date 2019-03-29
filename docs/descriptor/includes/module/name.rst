Name
--------

Key
    ``name``
Required
    Yes

Module identifier used to refer to the module, for example in list of modules to install
or in overrides.

.. warning::
    Please note that this key has a different purpose than the ``name`` key in :ref:`image descriptor <descriptor/image:Name>`.
    When defined in a module it defines the module name and **does not** override the image name.

.. code-block:: yaml

    name: "python_flask_module"