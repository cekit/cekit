Behave
==============

`Behave <https://behave.readthedocs.io/>`_ test framework uses `Gherkin language <https://docs.cucumber.io/gherkin/reference/>`_  to describe tests.

.. note::

    If you are not familiar with Behave, we suggest you read the
    `Behave documentation <https://behave.readthedocs.io/>`_ and the
    `Gherkin language reference <https://docs.cucumber.io/gherkin/reference/>`_
    before reading this chapter.
    This will make it much easier to understand how to write tests.

Introduction
--------------

To jump start you into Behave tests, consider the example below.

.. code-block:: cucumber

    Feature: OpenShift SSO tests

      Scenario: Test if console is available
        When container is ready
        Then check that page is served
            | property | value |
            | port     | 8080  |
            | path     | /auth/admin/master/console/#/realms/master |
            | expected_status_code | 200 |

In this specific case, a container will be created from the image and after boot a http
request will be made to the ``8080`` on the ``/auth/admin/master/console/#/realms/master`` context.
A successful reply is expected (return code ``200``).

We think that this way of describing what to test is concise and very powerful at the same time.

Behave tests overview
----------------------

Behave tests are defined in two parts: **steps** and **features**.

Features
^^^^^^^^^^^^^^^

Feature files define what should be tested. A feature file can contain multiple
scenarios grouped in features.

You can find a great `introduction to feature files in the Behave documentation <https://behave.readthedocs.io/en/latest/tutorial.html#feature-files>`_.
We do not want to repeat it here. If you think something is missing or needs more
explanation, please `open a ticket <https://github.com/cekit/cekit/issues/new>`_.

Image vs. module features
**************************

In CEKit you write features to test images. But depending on the part of the image you
write the test for, in many cases you will find that the test rather belongs to a **module**
rather than the image itself. In our experience we see that this is the most common case.

.. note::
    CEKit makes it possible to colocate tests with image source as well as module source. Please
    take a look at the :ref:`handbook/testing/behave:Test file locations` section for more information where these should be placed.

Placing feature files together with modules makes it easy to share the feature as well as tests.
Such tests could be run by multiple different images which use this particular module.

.. warning::
    There is a limitation in sharing module tests, please refer to the https://github.com/cekit/cekit/issues/421
    issue fore more information.

Steps
^^^^^^^^^^^^^^^

Steps define what can be tested in scenarios. Steps are written in Python.

As with features, `upstream documentation contains a section on steps <https://behave.readthedocs.io/en/latest/tutorial.html#python-step-implementations>`_.
We suggest to read this, if it does not answer all your questions, `let us know <https://github.com/cekit/cekit/issues/new>`_.

.. note::
    For information how you can write your own steps, please take a look at the
    :ref:`handbook/testing/behave:Writing custom steps` paragraph.

Default steps
**************

CEKit comes with a list of build-in steps that are available for use in
features. These steps are available in the `steps repository <https://github.com/cekit/behave-test-steps>`_.

.. hint::
    We encourage you to add or extend these steps instead of maintaining your own
    fork. We are happy to review your contributions! 👍

We will be `extending the default steps documentation <https://github.com/cekit/behave-test-steps/issues/9>`_
to cover all available steps with examples. In the meantime we suggest to look at the
`source code <https://github.com/cekit/behave-test-steps>`_ itself.

Usage
---------

Images can be tested by running:

.. code-block:: bash

        $ cekit test behave

The most basic usage would be to run the test with just the ``--image`` parameter to specify
which image should be tested.

.. code-block:: bash

        $ cekit test --image example/test:1.0 behave

Options
^^^^^^^^^

.. todo::

    Try to generate available options.

.. tip::

    For all available options, please use the ``--help`` switch.

* ``--wip`` -- Only run tests tagged with the ``@wip`` tag.
* ``--steps-url`` -- A git repository url containing `steps <https://pythonhosted.org/behave/tutorial.html#python-step-implementations>`_ for tests.
* ``--name`` -- *Scenario* name to be executed
* ``--include-re`` -- Regex of feature files which will be executed only
* ``--exclude-re`` -- Regex of feature files which will not be executed

Examples
^^^^^^^^^

In this section you can find some examples of frequently used tasks.

Running selected tests
***********************

CEKit makes it possible to run specific Scenario(s) only. To do it you need to run CEKit with
``--name <name of the test>`` command line argument.

.. note::
   ``--name`` switch can be specified multiple times and only the Scenarios
   matching all of the names are executed.

If you have following Scenario in your feature files:

.. code-block:: cucumber

    Scenario: Check custom debug port is available
        When container is started with env
            | variable   | value |
            | DEBUG      | true  |
            | DEBUG_PORT | 8798  |
        Then check that port 8798 is open

Then you can instruct CEKit to run this test in a following way:

.. code-block:: bash

    $ cekit test behave --name 'Check custom debug port is available'

Running selected features
*************************

CEKit also makes it possible to run specific feature(s) only. To do that, you need to run CEKit
tests with ``--include-re <regex of selected feature files'>`` command line argument.

For example, if you have feature files with names like ``basic1.feature``, ``basic2.feature``, ``advance1.feature``
and ``advance2.feature``, and you want to run only basic features, then you can instruct CEKit to run
only the basic features in a following way:

.. code-block:: bash

    $ cekit test behave --include-re basic

.. note::
   Here, ``'basic'`` is the regex that tells CEKit to consider only those feature files which contain ``'basic'``
   in their name, for ex. ``basic1.feature``.

Skipping tests
***********************

.. hint::
    See :ref:`handbook/testing/behave:Special tags` paragraph.

If there is a particular test which needs to be temporally disabled, you can use ``@ignore``
tag to disable it.

For example to disable following Scenario:

.. code-block:: cucumber

    Scenario: Check custom debug port is available
        When container is started with env
            | variable   | value |
            | DEBUG      | true  |
            | DEBUG_PORT | 8798  |
        Then check that port 8798 is open

You need to tag it with ``@ignore`` tag in a following way:

.. code-block:: cucumber

    @ignore
    Scenario: Check custom debug port is available
        When container is started with env
            | variable   | value |
            | DEBUG      | true  |
            | DEBUG_PORT | 8798  |
        Then check that port 8798 is open

Skipping selected features
**************************

CEKit also makes it possible to skip specific feature(s). To do that, you need to run CEKit
tests with ``--exclude-re <regex of selected feature files'>`` command line argument.

For example, if you have feature files with names like ``basic1.feature``, ``basic2.feature``, ``advance1.feature``
and ``advance2.feature``, and you do not want to run the advance features, then you can instruct CEKit to skip
the advance features in a following way:

.. code-block:: bash

    $ cekit test behave --exclude-re advance

.. note::
   Here, ``'advance'`` is the regex that tells CEKit to exclude those feature files which contain ``'advance'``
   in their name, for ex. ``advance1.feature``.

Test collection
----------------

It is important to understand how CEKit is collecting and preparing tests.

.. todo::
    Explain how tests are collected


Feature tags
---------------

CEKit selects tests to run using the Behave built-in
`tags mechanism <https://behave.readthedocs.io/en/latest/tutorial.html#controlling-things-with-tags>`_.

Tags are in format: ``@TAG_NAME``, for example: ``@jboss-eap-7``.

Below you can find several examples how tags could be used for managing tests across a set
of images:

Image tags
^^^^^^^^^^^^^^^^^^

CEKit derives two feature tag names from the name of the image being tested:

1. The image name itself (``name`` key in image descriptor), and
2. Everything before the first ``/`` in the image name, also known as *image family*.

..

    Example
        If you test the ``jboss-eap-7/eap7`` image,
        tests will be invoked with tags ``@jboss-eap-7`` and ``@jboss-eap-7/eap7``.

If ``--tag`` is specified, then the argument is used in place of the image
name for the process above.

    Example
        If you use ``--tag foo/bar`` parameter, then the tags used would be
        ``@foo`` and ``@foo/bar``.

Special tags
^^^^^^^^^^^^^^^^^^

``@wip``
    This is very special tag used while developing a test. Its purpose is to
    to limit the tests to be run to a subset you are working on. To achieve this
    you should mark your in-development test scenarios with the ``@wip`` tag and
    execute tests with ``--wip`` parameter. All scenarios not tagged with ``@wip``
    will be ignored.

``@ci``
    If CEKit is **not** running as a user called ``jenkins``, the tag ``@ci``
    is added to the list of **ignored** tags, meaning any tests tagged ``@ci`` are
    ignored and not executed.

    The purpose of this behavior is to ease specifying tests that are only
    executed when run within CI.

``@ignore``
    If a Scenario or Feature is tagged with ``@ignore`` these tests will be skipped.


Writing Behave tests
--------------------

.. todo::

    Write introduction

Test file locations
^^^^^^^^^^^^^^^^^^^^^^^

There are a few places where your tests can be stored:

1. ``tests`` directory next to the **image** descriptor
2. ``tests`` directory next to the **module** descriptor
3. ``tests`` directory in root of the module repository

The ``tests`` directory is structured as follows:

.. code-block:: text

        tests/features
        tests/features/*.feature
        tests/steps
        tests/steps/*.py

The ``tests/features`` directory is the place where you can drop your `behave
features. <https://behave.readthedocs.io/en/latest/tutorial/#features>`__

The ``tests/steps`` directory is optional and contains custom `steps
<https://behave.readthedocs.io/en/latest/tutorial/#python-step-implementations>`__
for the specific image/module.

Writing features
^^^^^^^^^^^^^^^^

The most important 

.. todo::
    TBD

Writing custom steps
^^^^^^^^^^^^^^^^^^^^^

.. todo::
    TBD

Running developed tests
^^^^^^^^^^^^^^^^^^^^^^^^

To be able to run only the test you develop you can either use the ``--name`` parameter
where you specify the scenario name you develop or use the ``--wip`` switch.

In our practice we found that tagging the scenario with ``@wip`` tag and using the ``--wip``
switch is a common practice, but it's up to you.
