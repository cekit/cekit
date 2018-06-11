``envs``
----------

Similar to labels -- we can specify environment variables that should be
present in the container after running the image. We provide ``envs``
section for this.

Environment variables can be divided into two types:

1. **Information environment variables** -- these are set and available in
   the image. This type of environment variables provide information to
   the image consumer. In most cases such environment variables *should not*
   be modified.

2. **Configuration environment variables** -- this type of variables are
   used to define environment variables used to configure services inside
   running container.

   These environment variables are **not** set during image build time but *can* be set at run time.

   Every configuration enviromnent variable should provide an example usage
   (``example``) and short description (``description``).

Please note that you could have an environment variable with both: a ``value``
and ``example`` set. This suggest that this environment variable could be redefined.

.. note::

    Configuration environment variables (without ``value``) are not
    generated to the build source. These can be used instead as a
    source for generating documentation.

.. code:: yaml

    envs:
        - name: "STI_BUILDER"
          value: "jee"
        - name: "JBOSS_MODULES_SYSTEM_PKGS"
          value: "org.jboss.logmanager,jdk.nashorn.api"
        - name: "OPENSHIFT_KUBE_PING_NAMESPACE"
          example: "myproject"
          description: "Clustering project namespace."
        - name: "OPENSHIFT_KUBE_PING_LABELS"
          example: "application=eap-app"
          description: "Clustering labels selector."
