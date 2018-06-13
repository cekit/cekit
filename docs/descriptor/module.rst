Module descriptor
=================

Module descriptor contains all information Cekit needs to introduce a feature to an image. Modules are used as libraries or shared building blocks across images.

It is very important to make a module self-containg which means that executing
scripts defined in the module's definition file should always end up in a state
where you could define the module as being `installed`.

Modules can be stacked -- some modules will be run before, some after you module.
Please keep that in mind that at the time when you are developing a module -- you don't
know how and when it'll be executed.

.. contents::

``name``
--------

This key is **required**.

Module name.

.. code:: yaml

    name: "python_flask_module"


.. include:: version.rst
.. include:: description.rst
.. include:: from.rst
.. include:: envs.rst
.. include:: labels.rst
.. include:: artifacts.rst
.. include:: packages.rst
.. include:: ports.rst
.. include:: user.rst
.. include:: volumes.rst	     
.. include:: modules.rst
.. include:: workdir.rst
.. include:: run.rst
.. include:: execs.rst	     
