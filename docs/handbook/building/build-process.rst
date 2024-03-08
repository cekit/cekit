Build process explained
========================


In this section we will go through the build process. You will learn what stages
there are and what is done in every stage.

High-level overview
------------------------

Let's start with a high-level diagram of CEKit.

.. graphviz::
    :align: center
    :alt: CEKit simple build process diagram

    digraph build_proces_high_level {
        bgcolor="transparent";
        rankdir="LR";
        style="filled";
        graph [fontsize="11", fontname="Open Sans", compound="true"];
        node [shape="box", fontname="Open Sans", fontsize="11"];

        descriptor [label="Image descriptor", style="filled", fillcolor="white"];
        image [label="Image", style="filled", fillcolor="white"];

        subgraph cluster_0 {
            style="dashed";
            fontcolor="red";
            node [style="filled"];
            label = "CEKit";
            penwidth = "2";
            color="dimgrey";

            generate [label="Generate"];
            build [label="Build"];
        }

        descriptor -> generate [lhead=cluster_0, color="red"];
        generate -> build [color="red"];
        build -> image [ltail=cluster_0, color="red"];

    }

Main input to CEKit is the :doc:`image descriptor</descriptor/image>`. It defines the image.
This should be the definitive description of the image; what it is, what goes in and where and
what should be run on boot.

Preparation of the image CEKit divides into two phases:

#. Generation phase
    Responsible for preparing everything required to build the image using selected builder.
#. Build phase
    Actual build execution with selected builder.

Result of these two phases is the image.

Let's discuss it in details.

Build process in details
------------------------------

As :ref:`mentioned above <handbook/building/build-process:High-level overview>` the CEKit build process is divided into two phases:

#. Generation phase
#. Build phase

In this section we will go through these phases in detail to see what's happening in each. Below you
can find diagram that shows what is done from beginning to the end when you execute CEKit.

.. graphviz::
    :align: center
    :alt: CEKit build process diagram
    :name: build-process-diagram

     digraph build_process {
        graph [fontsize="11", fontname="Open Sans", compound="true"];
        node [shape="box", fontname="Open Sans", fontsize="10"];
        bgcolor="transparent";

        subgraph cluster_out {
            style="invis";
            start [label="START", shape="circle", style="bold,filled", fillcolor="white"];
            end [label="END", shape="circle", style="bold,filled", fillcolor="white"];

            subgraph cluster_0 {
                style="dashed";
                node [style="filled"];
                penwidth = "1";
                color="dimgrey";

                read [label="Read descriptor", href="#reading-image-descriptor"];
                overrides [label="Apply overrides", href="#applying-overrides"];
                modules [label="Prepare modules", href="#preparing-modules"];
                artifacts [label="Handle artifacts", href="#handling-artifacts"];
                generate [label="Generate files", href="#generating-required-files"];
            }

            subgraph cluster_1 {
                style="dashed";
                node [style="filled"];
                penwidth = "1";
                color="dimgrey";
                build [label="Execute build", href="#build-execution"];
            }
        }

        label_generate [label="Generate phase", shape="plaintext", fontsize="11", fontcolor="red"];
        label_build [label="Build phase", shape="plaintext", fontsize="11", fontcolor="red"];

        start -> read -> overrides -> modules -> artifacts -> generate -> build -> end [color="red"];
        overrides -> label_generate [style="invis"];
        generate -> label_build [style="invis"];
     }

The build process is all about preparation of required content so that the selected
builder could create an image out of it. Depending on the builder, this could mean different
things. Some builders may require generating Dockerfiles, some may require generating additional
files that instruct the builder itself how to build the image or from where to fetch artifacts.

Reading image descriptor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this phase the image descriptor is read and parsed. If the description is not in YAML format,
it won't be read.

Next step is to prepare an **object representation** of the descriptor. In CEKit internally we do not
work on the dictionary read from the descriptor, but we operate on objects. Each section is converted individually
to object and **validated according to the schema** for the section.

This is an important step, because it ensures that the image descriptor uses correct schema.

Applying overrides
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Applying :doc:`overrides</handbook/overrides>` is the next step. There can be many overrides specified. Some of them
will be declared on CLI directly, some of them will be YAML files. We need to create an array of overrides
because the **order in which overrides are specified matters**.

Each override is converted into an object too, and yes, you guessed it -- it's validated at the same time.

Last thing to do is to apply overrides on the image object we created before, in order.

Preparing modules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Next thing to do is to prepare :doc:`modules</descriptor/module>`. If there are any module repositories defined, we need to
fetch them, and read. In most cases this will mean executing ``git clone`` command for each module repository,
but sometimes it will be just about copying directories available locally.

All module repositories are fetched into a temporary directory.

For each module repository we read every module descriptor we can find. Each one
is converted into an object and validated as well.

Once everything is done, we have a module registry prepared, but this is not enough.

Next step is to apply module overrides to the image object we have. Modules are
actually overrides with the difference that modules encapsulate a defined functionality whereas
overrides are just modifying things.

To do this we iterate over all modules that are defined to install and we try to find them in the module registry
we built before. If there is no such module or the module version is different from what we request,
the build will fail. If the requirement is satisfied the module is applied to the image object.

The last step is to copy only required modules (module repository can contain many modules)
from the temporary directory to the final target directory.

Handling artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each module and image descriptor itself can define :ref:`artifacts <descriptor/image:Artifacts>`.

In this step CEKit is going to handle all defined artifacts for the image. For each defined
artifact CEKit is going to fetch it. If there will be a problem while fetching the artifact,
CEKit will fail with information why it happened.

Each successfully fetched artifact is automatically added to :doc:`cache</handbook/caching>` so that
subsequent build will be executed faster without the need to download the artifact again.

Generating required files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When we have all external content handled and the image object is final we can generate required files.
Generation is tightly coupled with the selected builder because different builders require different
files to be generated.

For example Docker builder requires Dockerfile to be generated, but the OSBS builder requires
additional files besides the Dockerfile.

For Dockerfiles we use a template which is populated which can access the image object properties.

Build execution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Final step is to execute the build using selected builder.

Resulting image sometimes will be available on your localhost, sometimes in some remote
registry. It all depends on the builder.
