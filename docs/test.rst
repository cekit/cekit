Testing images
==============

Cekit is able to run `behave <https://behave.readthedocs.io/>`_ based
tests for images. We suggest you read the Behave documentation before reading
this chapter.

An image can be tested by running:

.. code:: bash
	  
	  $ cekit test

**Test options**

* ``--test-wip`` -- only run tests tagged with the ``@wip`` tag.
* ``--test-steps-url`` -- a git repository url containing `steps <https://pythonhosted.org/behave/tutorial.html#python-step-implementations>`_ for tests.
* ``--tag altname`` --  overrides the name of the Image used for testing to ``altname``. Only the first occurrence of this argument is honoured.
* ``--test-name`` -- part of the Scenario name to be executed


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

Cekit comes with a list of build-in steps that are available for use in
tests. See the `steps repository <https://github.com/jboss-openshift/cekit-test-steps>`_.

Where necessary we encourage people to add or extend these steps.

**Tags**

Cekit selects which tests to run via the *tags* mechanism. Here are several
examples of ways ways that tags could be used for managing tests across a set
of related images:

1. `Product tags`
   
   Tags based on image names. Cekit derives two test tag names from the
   name of the Image being tested. The whole image name is converted into one
   tag, and everything before the first '/' character is converted into
   another.
   **Example**: If you are testing the ``jboss-eap-7/eap7`` image,
   tests will be invoked with tags ``@jboss-eap-7`` and ``@jboss-eap-7/eap7``.

   If ``--tag`` is specified, then the argument is used in place of the Image
   name for the process above.
   **Example** If you provided ``--tag foo/bar``, then the tags used would be
   ``@foo`` and ``@foo/bar``.

2. `Wip tags`
   
   This is very special behavior used mainly in development. Its purpose is to
   to limit the tests to be run to a subset you are working on. To achieve this
   you should mark your in-development test scenarios with the ``@wip`` tag and
   run ``cekit test --test-wip``. All other scenarios not tagged ``@wip``
   will be ignored.

3. `The @ci tag`

   If ``cekit`` is not running as a user called ``jenkins``, the tag ``@ci``
   is added to the list of ignored tags, meaning any tests tagged ``@ci`` are
   ignored and not executed.

   The purpose of this behavior is to ease specifying tests that are only
   executed when run within Jenkins CI.


Running specific test
---------------------

Cekit enables you to run specific Scenario only. To do it you need to run Cekit with
``--test-name <name of the tests>`` command line argument.

**Example**: If you have following Scenario in your feature files:

.. code:: cucumber

	    Scenario: Check custom debug port is available
            When container is started with env
            | variable   | value |
            | DEBUG      | true  |
            | DEBUG_PORT | 8798  |
            Then check that port 8798 is open


Then you can instruct Cekit to run this test in a following way:

.. code:: bash

          $ cekit test --test-name 'Check custom debug port is available'

.. note::
   ``--test-name`` switch can be specified multiple times and only the Scenarios
   matching all of the names are executed. 
