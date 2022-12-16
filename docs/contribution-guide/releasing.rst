Release Process
=========================

To release a new version of CEKit a number of steps must be taken.



GitHub
------------

Automated Process
^^^^^^^^^^^^^^^^^^

The automated process uses https://pypi.org/project/zest.releaser to perform the correct steps. This is installed by the Pipfile development environment.

* Clone ``git@github.com:cekit/cekit.git`` (from https://github.com/cekit/cekit )
* Run ``make release`` and follow the prompts.

    .. note:: A ``.pypirc`` should be configured according to https://packaging.python.org/specifications/pypirc for PyPi uploads.

    .. note:: It is recommended to use a 3 digit version specification when prompted (e.g. ``3.9.10``, ``3.10.2``).

    .. note:: The variable ``TYPE`` may be used to denote the type of release i.e. ``TYPE=--breaking`` (for a major), ``TYPE=--feature`` (for a minor) or ``TYPE=""`` for a micro. The default is ``--feature``. For example ``make TYPE=--breaking release``

Manual Process (reference only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Switch to main branch
* Ensure you have the latest code: ``git reset --hard upstream/main``
* Merge develop: ``git merge develop -X theirs`` and in the commit message enter: ``Release <version>``
* Edit ``cekit/version.py`` file and put ``<next-version>``, add that file and amend the previous commit.
* Tag repository: ``git tag <version>``
* Push code to main: ``git push upstream main``
* Push tags: ``git push upstream --tags``
* Push a release to PyPi (https://pypi.org/project/cekit/ ) via ``make clean release`` (requires twine: https://pypi.org/project/twine/ which is also available as a RPM in Fedora)
* Update version on develop to point to next major/minor release

    .. note::
        Note when you see line like this: Uploading distributions to https://upload.pypi.org/legacy/ enter blindly your username on PyPi and hit enter, it will ask you for password.


RPM Builds
------------

Once the GitHub release is complete RPM builds for Fedora and EPEL can be performed.

A pre-requisite for this is that the developer running the updates has a `Fedora Account System <https://fedoraproject.org/wiki/Account_System?rd=Infrastructure/AccountSystem>`__ account,
has Kerberos authentication setup as described `here <https://fedoraproject.org/wiki/Infrastructure/Kerberos>`__ and has correctly
setup `Pagure <https://docs.pagure.org/pagure/usage/>`__  with a SSH key `here <https://pagure.io/settings#nav-ssh-tab>`__.

Ensure the following RPM packages are installed on your system:

* fedora-packager
* fedora-packager-kerberos
* krb5-workstation
* rpmdevtools
* fedpkg

The CEKit RPM repository is stored on Pagure at https://src.fedoraproject.org/rpms/cekit

Unfortunately several manual steps must be done next:

1. Use ``fkinit -u <user-id>`` to create your Kerberos principal. Note that by ``klist`` will only show the last created, so use ``klist -A`` to show all.
2. Switch to the main branch first (which is an alias for Rawhide).
3. Update the spec file with the latest release. Note that the ``Release`` version should be reset to zero for the next command. For example, the changes might be:

.. code-block:: diff

   Name:           %{modname}
  -Version:        3.9.0
  -Release:        3%{?dist}
  +Version:        3.12.0
  +Release:        0%{?dist}
   Summary:        Container image creation tool
   License:        MIT
   URL:            https://cekit.io
  -Source0:        https://github.com/cekit/cekit/archive/%{release_version}/%{name}-%{release_version}.tar.gz
  +Source0:        https://github.com/cekit/cekit/archive/refs/tags/%{version}.tar.gz



4. Run ``spectool -g cekit.spec`` which will parse the ``Source0`` and download the sources.
5. Run ``rpmdev-bumpspec cekit.spec -c "Release 3.12.0"`` which will update the ``Release`` version and generate a change log entry.
6. Run ``fedpkg new-sources *tar.gz`` to upload the new version. Note that you can explicitly specify the tar file and the system won't re-upload any old tar files. The lookaside cache applies to all branches so only a single upload is required.
7. Then commit and push the changes.
8. Run a build via ``fedpkg build --scratch``
9. If that succeeds then run ``fedpkg build`` (or ``fedpkg build --nowait``)

Then for each branch active in https://src.fedoraproject.org/rpms/cekit/branches switch branch (with ``fedpkg switch-branch f33``) and repeat steps 3->9. It *may* be possible to simply cherry-pick or merge the commit from step 7, then perform steps 8 and 9.

Finally using https://bodhi.fedoraproject.org/updates/?packages=cekit submit all non-Rawhide packages as updates. For Rawhide, as everything is testing, its automatic. Once the packages have reached appropriate karma or the requisite time has passed they may be pushed.



Final Steps
-------------

* Prepare the `release notes <https://github.com/cekit/cekit/releases>`__
* Write announcement blog post for https://cekit.io/
* Update http://readthedocs.io/ to show new version
* Announce on GChat/Twitter/Email
