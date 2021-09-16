Submitting changes
=========================

First of all; **thank you** for taking the effort to modify the code yourself and submitting your work
so others can benefit from it!

Target branch
--------------

All development is done in the ``develop`` branch. This branch is what will the next major or minor CEKit release
look like and this is the place you should submit your changes.

.. note::
    Submitting a pull request against the ``main`` branch may result in a request to rebase it against ``develop``.

In case a fix needs to target the currently released version (a bugfix), the commit will be manually cherry-picked
by the CEKit team.

Review process
---------------

Each submitted pull request is reviewed by at least one CEKit team member. We may ask you for some changes in the code or

Tests
--------

We expect that each pull request contains a test for the change. It's unlikely that a PR will be merged without a test, sorry!

Of course, if the PR is not about code change, but for example a documentation update, you don't need to write a test for it :)

GitHub automation
--------------------

Please reference the issue in the PR to utilise GitHubs ability to
`automatically close issues <https://help.github.com/en/articles/closing-issues-using-keywords>`__. You can add e.g.
``Fixes #nnn`` somewhere in the initial comment.
