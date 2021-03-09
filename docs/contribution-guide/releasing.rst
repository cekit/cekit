Release Process
=========================

To release a new version of CEKit a number of steps must be taken.



GitHub
------------

Automated Process
^^^^^^^^^^^^^^^^^^

The automated process uses https://pypi.org/project/zest.releaser to perform the correct steps. This is installed via Pip automatically by the Makefile.

* Clone https://github.com/cekit/cekit.git
* Run ``make release`` and follow the prompts.


    .. note:: A ``.pypirc`` should be configured according to https://packaging.python.org/specifications/pypirc for PyPi uploads.

Manual Process (reference only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Switch to master branch
+ Ensure you are latest code: ``git reset --hard upstream/master``
* Merge develop: ``git merge develop -X theirs`` and in the commit message enter: ``Release <version>``
* Edit ``cekit/version.py`` file and put ``<next-version>``, add that file and amend the previous commit.
* Tag repository: ``git tag <version>``
* Push code to master: ``git push upstream master``
* Push tags: ``git push upstream --tags``
* Push a release to PyPi (https://pypi.org/project/cekit/ ) via ``make clean release`` (requires twine: https://pypi.org/project/twine/ which is also available as a RPM in Fedora)

    .. note::
        Note when you see line like this: Uploading distributions to https://upload.pypi.org/legacy/ enter blindly your username on PyPi and hit enter, it will ask you for password.


Final Steps
-------------

* Prepare the `release notes <https://github.com/cekit/cekit/releases>`__
* Write announcement blog post for https://cekit.io/
* Build and submit in Bodhi RPMs for Fedora and EPEL
* Update http://readthedocs.io/ to show new version
* Update version on develop to point to next major/minor release
* Announce on GChat/Twitter/Email
