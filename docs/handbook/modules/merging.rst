Module processing
=========================

.. contents::
    :backlinks: none

.. note::
    This chapter applies to :doc:`builder engines </handbook/building/builder-engines>` that use Dockerfile as the input.


Understanding how modules are merged together is important. This knowledge will let you
introduce modules that work better together and make rebuilds faster which is an important
aspect of the image and module development.

Order is important
--------------------

Installation order of modules is extremely important. Consider this example:

.. code-block:: yaml
    :linenos:
    :emphasize-lines: 15-18

    modules:
        repositories:
            # Add local modules located next to the image descriptor
            # These modules are specific to the image we build and are not meant
            # to be shared
            - path: modules

            # Add a shared module repository located on GitHub. This repository
            # can contain several modules.
            - git:
                url: https://github.com/cekit/example-common-module.git
                ref: master

        # Install selected modules (in order)
        install:
            - name: jdk8
            - name: user
            - name: tomcat

On lines 16-18 we have defined a list of modules to be installed. These are installed
in the order as they are defined (from top to bottom). This means that the first module installed
will be ``jdk8`` followed by ``user`` and the ``tomcat`` module will be installed last.

The same order is used later in the module merge process too.

.. note::
    Defining module *repositories* in the ``repositories`` section does not require any particular order.
    Modules are investigated after all modules repositories are fetched.

Module processing in template
-------------------------------

Each module descriptor marked to be installed can :doc:`define many different things </descriptor/module>`.
All this metadata needs to be merged correctly into a single image, so that the resulting image is
what we really expected.

This is where templates come into play. We use a `template <https://github.com/cekit/cekit/blob/main/cekit/templates/template.jinja>`__
to generate the Dockerfile that is later fed into the builder engine.

This section will go through it and explain how we combine everything together in the template.

.. note::
    Sections not defined in the module descriptor are simply skipped.

.. graphviz::
    :align: center
    :alt: Module installation
    :name: module-installation-diagram

     digraph module_installation {
        graph [fontsize="11", fontname="Open Sans", compound="true"];
        node [shape="box", fontname="Open Sans", fontsize="10"];

        packages [label="Package installation", href="#packages"];
        envs [label="Environment variables", href="#environment-variables"];
        labels [label="Labels", href="#labels"];
        ports [label="Ports", href="#ports"];
        execs [label="Executions", href="#executions"];
        volumes [label="Volumes", href="#volumes"];

        packages -> envs -> labels -> ports -> execs -> volumes;
     }


Packages
^^^^^^^^^^^

The first thing done for each module is the package installation for all :ref:`packages defined in the module <descriptor/module:Packages to install>`.
We do not clean the cache on each run, because this
would slow subsequent package manager executions. You should also not worry about it taking too much space,
because every image is squashed (depends on builder though).

Package installation is executed as ``root`` user.

.. note::
    It is only possible to define a single package manager for an image (although multi-stage images may have
    different package managers). A package manager may be defined in a module or in an image (the latter takes
    precedence).

Environment variables
^^^^^^^^^^^^^^^^^^^^^^^

Each defined :ref:`environment variable <descriptor/module:Environment variables>` is added to the Dockerfile.

.. note::
    Please note that you can define an :ref:`environment variable without value <descriptor/module:Environment variables>`.
    In such case, the environment will not be added to Dockerfile as it serves only an information purpose.

Labels
^^^^^^^^^^^^^^^^^^^^^^^

Similarly to environment variables, :ref:`labels <descriptor/module:Labels>` are added too.

Ports
^^^^^^^^^^^^^^^^^^^^^^^

All :ref:`ports <descriptor/module:Ports>` defined in the descriptor are exposed as well.

Executions
^^^^^^^^^^^^^^^^^^^^^^^

This is probably the most important section of each module. This is where the actual module installation is done.
Each script defined in the :ref:`execute section <descriptor/module:Execute>` is converted to a ``RUN`` instruction.

The user that executes the script can be modified with the ``user`` key.

Volumes
^^^^^^^^^^^^^^^^^^^^^^^

Last thing is to add the :ref:`volume <descriptor/module:Volumes>` definitions.

Flattening nested modules
---------------------------

Above example assumed that modules defined in the image descriptor do not have any child modules. This
is not always true. Each module can have :ref:`dependency on other modules <descriptor/module:Modules>`.

In this section we will answer the question: what is the order of modules in case where we have a hierarchy of modules requested to be installed?

Best idea to explain how module dependencies work is to look at some example. For simplicity, only the ``install`` section will be shown:

.. code-block:: yaml

    # Module A

    name: "A"
    modules:
        # This module requires two additional modules: B and C
        install:
            - name: B
            - name: C

.. code-block:: yaml

    # Module B

    name: "B"
    modules:
        # This module requires one additional module: D
        install:
            - name: D

.. code-block:: yaml

    # Module C

    # No other modules required
    name: "C"

.. code-block:: yaml

    # Module D

    # No other modules required
    name: "D"

.. code-block:: yaml

    # Module E

    # No other modules required
    name: "E"

.. code-block:: yaml

    # Image descriptor

    name: "example/modules"
    version: "1.0"
    modules:
        repositories:
            - path: "modules"
        install:
            - name: A
            - name: E


To make it easier to understand, below is the module dependency diagram. Please note that this diagram
does not tell you the order in which modules are installed, but only what modules are requested.

.. graphviz::
    :align: center
    :alt: Module dependency
    :name: module-dependency-diagram

     digraph module_installation {
        graph [fontsize="11", fontname="Open Sans", compound="true"];
        node [shape="circle", fontname="Open Sans", fontsize="10"];

        image [label="Image descriptor", shape="box"];

        A -> B;
        A -> C;
        B -> D;

        image -> E;
        image -> A;

     }

The order in which modules will be installed is:

#. D
#. B
#. C
#. A
#. E

How it was determined?

.. code-block:: python

    modules = []

We start with the first module defined: *A*. We find that it has some dependencies: modules *B* and *C*.
This means that we need to investigate these modules first, because these need to be installed before module
*A* can be installed.

We investigate module *B*. This module has one dependency: *D*, so we investigate it
and we find that this module has no dependency. This means that we can install it first.

.. code-block:: python

    modules = ["D"]

Then we go one level back and we find that module *B* has no other requirements besides module *D*, so we can install it too.

.. code-block:: python

    modules = ["D", "B"]

We go one level back and we're now investigating module *C* (a requirement of module *A*). Module *C*
has no requirements, so we can install it.

.. code-block:: python

    modules = ["D", "B", "C"]

We go one level back. We find that module *A* dependencies are satisfied, so we can add module *A* too.

.. code-block:: python

    modules = ["D", "B", "C", "A"]

Last module is the module *E*, with no dependencies, we add it too.

.. code-block:: python

    modules = ["D", "B", "C", "A", "E"]

This is the final order in which modules will be installed.

Understanding the merge process
--------------------------------

Now you know that we iterate over all modules defined to install and apply it one by one, but how
it influences the build process? It all depends on the `Dockerfile instructions <https://docs.docker.com/engine/reference/builder/>`__
that was used in the template. Some of them will overwrite previous values (``CMD``), some of them will just add
values (``EXPOSE``). Understanding how Dockerfiles work is important to make best usage of CEKit with
builder engines that require Dockerfile as the input.

Environment variables and labels can be redefined. If you define a value in some module, another module
later in the sequence can change its effective value. This is a feature that can be used to redefine
the value in subsequent modules.

Volumes and ports are just adding next values to the list.

.. note::
    Please note that there is no way to actually **remove**
    a volume or port in subsequent modules. This is why it's important to create modules that define only what is needed.

    We suggest to not add any ports or volumes in the module descriptors leaving it to the image descriptor.

Package installation is not merged at all. Every module which has defined packages to install will be processed one-by-one
and for each module a :ref:`package manager <descriptor/module:Package manager>` will be executed to install requested packages.

Same approach applies to the ``execute`` section of each module. All defined will be executed in the requested order.
