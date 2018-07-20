Labels
------

.. note::

    Learn more about `standard labels in container images <https://github.com/projectatomic/ContainerApplicationGenericLabels>`_.

Every image can include labels. Cekit makes it easy to do so with the ``labels`` section.

.. code:: yaml

    labels:
        - name: "io.k8s.description"
          value: "Platform for building and running JavaEE applications on JBoss EAP 7.0"
        - name: "io.k8s.display-name"
          value: "JBoss EAP 7.0"
