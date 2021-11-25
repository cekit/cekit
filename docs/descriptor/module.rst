Module descriptor
=================

Module descriptor contains all information CEKit needs to introduce a feature to an image.
Modules are used as libraries or shared building blocks across images.

It is very important to make a module self-contained which means that executing
scripts defined in the module's definition file should always end up in a state
where you could define the module as being `installed`.

Modules can be stacked -- some modules will be run before, some after your module.
Please keep that in mind at the time you are developing your module -- you don't
know how and when it'll be executed.

.. contents::
    :backlinks: none

.. include:: includes/module/name.rst
.. include:: includes/module/execute.rst
.. include:: common_keys.rst
.. include:: includes/module/packages.rst
