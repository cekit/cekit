Environment variables
-------------------------

Key
    ``envs``
Required
    No

Similar to `labels <#labels>`__ -- we can specify environment variables that should be
present in the container after running the image. We provide ``envs``
section for this.

Environment variables can be divided into two types:

#.  **Information environment variables**

    These are set and available in
    the image. This type of environment variables provide information to
    the image consumer. In most cases such environment variables *should not*
    be modified.

    It is possible to define a ``description`` for an information variable.

#.  **Configuration environment variables**

    This type of variables are used to define environment variables used to configure services inside
    running container.
    These environment variables are **not** set during image build time but *can* be set at run time.

    The primary difference to the above type is the lack of a ``value`` definition. Every configuration environment variable should provide an example usage (``example``) and short description (``description``).

.. note::

    Please note that you could have an environment variable with both a ``value`` and ``example`` set.
    This implies that this environment variable could be redefined.

.. note::

    Configuration environment variables (**without** a ``value`` key) are not
    generated to the build source (the Dockerfile). These can be used instead as a
    source for generating documentation.

.. code-block:: yaml

    envs:
        # Configuration env variables below
        # These will be added to container
        - name: "STI_BUILDER"
            value: "jee"
        - name: "JBOSS_MODULES_SYSTEM_PKGS"
            value: "org.jboss.logmanager,jdk.nashorn.api"

        # Information env variables below
        # These will NOT be defined (there is no value)
        - name: "OPENSHIFT_KUBE_PING_NAMESPACE"
            example: "myproject"
            description: "Clustering project namespace."
        - name: "OPENSHIFT_KUBE_PING_LABELS"
            example: "application=eap-app"
            description: "Clustering labels selector."
