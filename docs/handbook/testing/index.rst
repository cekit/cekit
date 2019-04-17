Image testing
==============

CEKit makes it possible to run tests against images. The goal is to make it possible
to test images using different frameworks.

Using different frameworks allows to define specialized tests. For example you can write tests
that focus only parts of the image (you can think about unit tests) or the image (or even a set of images
even!) as a whole which is similar to integration testing.

.. tip::

    We strongly recommend that a test is written for every feature that is added to the image.

Currently we support following test frameworks:

.. toctree::
    :titlesonly:
    
    behave