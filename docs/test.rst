Testing image
=============

Concreate is able to run `behave <https://pythonhosted.org/behave/>`_ based test for the image. We suggest you to read behave docs before reading this chapter.

To can test the image by running:

.. code:: bash
	  $ concreate test

**Test options**

* ``--test-wip`` -- run only test tagged with ``@wip`` tag.

How tests works
---------------
Behave test are separate to two parts steps and features. You can place tests in test sub directory next
to the image descriptor, module descriptor or in a root of a git repository which contains the modules.

We strongly recommend that a test is written for every feature that is added to the images. For the list of steps that are available for use in tests, see the `steps repository <https://github.com/jboss-openshift/concreate-test-steps>`_. Where necessary we encourage people to add or extend the steps.

**Tags**
Concreate is selecting which test to run via tags mechanism. There are two way the tags are used:

1. `Product tags`
   
   These tags are based on product names. When a product image is tested, concreate uses tag containing image name and its product family name.
   **Example**: If you are testing ``jboss-eap-7/eap7`` image, test will be invoked with tag ``@jboss-eap-7`` and ``@jboss-eap-7/eap7``.

2. `Wip tag`
   
   This is very special behavior used mainly in development. It servers purpose you want to limit test to be run to a subset you are working on. To achieve this you should mark your test scenario with ``@wip`` tag and run ``concreate test --wip-test``
