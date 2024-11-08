Image Descriptor and Modules
============================


.. note::
    This chapter applies to :doc:`builder engines </handbook/building/builder-engines>` that use Dockerfile as the input.


While :doc:`module processing </handbook/modules/merging>` chapter covered the template processing modules this section
describes how the image processing interacts with the module processing.


.. graphviz::
    :align: center
    :alt: Module installation
    :name: module-installation-diagram

     digraph module_installation {
        bgcolor="transparent";
        graph [fontsize="11", fontname="Open Sans", compound="true", splines=ortho, nodesep=0.5, ranksep=0.75];
        node [shape="box", fontname="Open Sans", fontsize="10", style="filled", fillcolor="white"];

        // main rendering
        subgraph cluster_0 {
                bgcolor="lightgrey"
                label="Main Rendering Generation";
                builder [label="Builder image handling"];
                from [label="FROM generation"];
                extra [label="Extra directory copying"];
                image [label="Image Processing"];
                cleanup [label="Cleanup"];
                final [label="Final stages", href="#final-stages"];
        }

        // process_image
        subgraph cluster_1 {
                bgcolor="lightgrey"
                label="Image Rendering";
                cachito [label="Cachito Support", rank=same];
                arg [label="Main image ARG handling"];
                repo [label="Repository Management"];
                module [label="Included Module Processing"];
                complete_image [label="Final Image stages", href="#final-image-stages"];
        }

        // process_module
        subgraph cluster_2 {
                bgcolor="lightgrey"
                artifact [label="Artifact copying", rank=same];
                pkg_install [label="Package installation"];
                ports [label="Expose Ports"];
                run [label="Run scripts"];
                volumes [label="Configure volumes"];
        }

        // graph control
        builder -> from -> extra -> image -> cleanup -> final;
        cachito -> repo -> arg -> module -> complete_image;
        artifact -> pkg_install -> ports -> run -> volumes;

        // subgraph links
        builder -> cachito[constraint=false, color="red"];
        image -> cachito[constraint=false, color="red"];
        module -> artifact[constraint=false, color="red"];
        complete_image -> artifact[constraint=false, color="red"];
    }


Final Stages
"""""""""""""""""""""""

This encompasses defining the ``USER``, the ``WORKDIR``, and ``ENTRYPOINT``. Finally the ``RUN`` command is generated.

Final Image Stages
"""""""""""""""""""""""

This encompasses the final part of the generation for the image descriptor which may include e.g. package
installation or artifact handling.

.. note::
    Note that the main image handling happens **after** modules have been included and processed.

    The only exception to this is ``args`` which are injected first.