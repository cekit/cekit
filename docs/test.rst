Testing image
=============

Concreate is able to run `behave <https://pythonhosted.org/behave/>`_ based test for the image. We suggest to read behave documentation before reading this chapter.

Image can be tested by running:

.. code:: bash
	  
	  $ concreate test

**Test options**

* ``--test-wip`` -- run only tests tagged with ``@wip`` tag.

About Tests
-----------
Behave tests are separate to two parts steps and features. You can place tests in ``tests`` directory next
to the image descriptor, module descriptor or in a root of a git repository which contains the modules.

The tests directory is structured in following way:

.. code::
   
          tests/features
          tests/features/amq.features
          tests/steps
          tests/steps/custom_steps.py


The ``tests/features`` directory is the place where you can drop your custom developed `behave features. <https://pythonhosted.org/behave/gherkin.html>`_

The ``tests/steps`` directory is optional and contains custom `steps <https://pythonhosted.org/behave/tutorial.html#python-step-implementations>`_ for specific image/module.

We strongly recommend that a test is written for every feature that is added to the image.
For the list of steps that are available for use in tests, see the `steps repository <https://github.com/jboss-openshift/concreate-test-steps>`_.
Where necessary we encourage people to add or extend the steps.

**Tags**

Concreate is selecting which test to run via tags mechanism. There are two way the tags are used:

1. `Product tags`
   
   These tags are based on product names. When a product image is tested, concreate uses tag containing image name and its product family name.
   **Example**: If you are testing ``jboss-eap-7/eap7`` image, test will be invoked with tag ``@jboss-eap-7`` and ``@jboss-eap-7/eap7``.

2. `Wip tags`
   
   This is very special behavior used mainly in development. It servers purpose you want to limit test to be run to a subset you are working on. To achieve this you should mark your test scenario with ``@wip`` tag and run ``concreate test --test-wip``
