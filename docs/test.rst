Testing images
==============

Concreate is able to run `behave <https://pythonhosted.org/behave/>`_ based
tests for images. We suggest you read the Behave documentation before reading
this chapter.

An image can be tested by running:

.. code:: bash
	  
	  $ concreate test

**Test options**

* ``--test-wip`` -- only run tests tagged with the ``@wip`` tag.
* ``--test-steps-url`` -- a git repository url containing `steps <https://pythonhosted.org/behave/tutorial.html#python-step-implementations>`_ for tests.
* ``--tag @sometag`` --  only run tests tagged with e.g. ``@sometag``. Only the first occurrence of this argument is honoured.


About Tests
-----------

Behave tests are defined in two separate parts: steps and features.

You can place the files defining tests in a ``tests`` directory next to the
image descriptor, module descriptor or in a root of a git repository which
contains the modules.

The tests directory is structured as follows:

.. code::
   
          tests/features
          tests/features/amq.feature
          tests/steps
          tests/steps/custom_steps.py


The ``tests/features`` directory is the place where you can drop your `behave
features. <https://pythonhosted.org/behave/gherkin.html>`_

The ``tests/steps`` directory is optional and contains custom `steps
<https://pythonhosted.org/behave/tutorial.html#python-step-implementations>`_
for the specific image/module.

We strongly recommend that a test is written for every feature that is added to the image.

Concreate comes with a list of build-in steps that are available for use in
tests. See the `steps repository <https://github.com/jboss-openshift/concreate-test-steps>`_.

Where necessary we encourage people to add or extend these steps.

**Tags**

Concreate selects which tests to run via the *tags* mechanism. Here are three
ways that tags could be used for managing tests across a set of related images:

1. `Product tags`
   
   Tags based on product names. When a product image is tested, concreate uses
   tags containing the image name and its product family name.  **Example**: If
   you are testing ``jboss-eap-7/eap7`` image, test will be invoked with tag
   ``@jboss-eap-7`` and ``@jboss-eap-7/eap7``.

2. `Wip tags`
   
   This is very special behavior used mainly in development. Its purpose is to
   to limit the tests to be run to a subset you are working on. To achieve this
   you should mark your in-development test scenarios with the ``@wip`` tag and
   run ``concreate test --test-wip``.

3. `Custom tags`

   You can restrict tests to those for a particular image using the ``--tag``
   option. **Example**: To run only the tests for image 'foo' you can run
   ``concreate test --tag foo``
