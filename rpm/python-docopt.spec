%if 0%{?rhel}
%global with_python3 0
%else
%global with_python3 1
%endif

%global pypi_name docopt

Name:           python-docopt
Version:        0.6.2
Release:        6%{?dist}
Summary:        Pythonic argument parser, that will make you smile

License:        MIT
URL:            https://github.com/docopt/docopt
Source0:        %{url}/archive/%{version}/%{pypi_name}-%{version}.tar.gz

BuildArch:      noarch

%description
Isn't it awesome how optparse and argparse generate help messages
based on your code?!

Hell no! You know what's awesome? It's when the option parser is
generated based on the beautiful help message that you write yourself!
This way you don't need to write thisstupid repeatable parser-code,
and instead can write only the help message--*the way you want it*.

%package -n python2-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python2-%{pypi_name}}
BuildRequires:  python2-devel

%if 0%{?rhel}
BuildRequires:  pytest
Requires:       python-setuptools
%else
BuildRequires:  python2-pytest
BuildRequires:  python2-setuptools
%endif

%description -n python2-%{pypi_name}
Isn't it awesome how optparse and argparse generate help messages
based on your code?!

Hell no! You know what's awesome? It's when the option parser is
generated based on the beautiful help message that you write yourself!
This way you don't need to write thisstupid repeatable parser-code,
and instead can write only the help message--*the way you want it*.

Python 2 version.

%if 0%{?with_python3}
%package -n python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pytest

%description -n python3-%{pypi_name}
Isn't it awesome how optparse and argparse generate help messages
based on your code?!

Hell no! You know what's awesome? It's when the option parser is
generated based on the beautiful help message that you write yourself!
This way you don't need to write thisstupid repeatable parser-code,
and instead can write only the help message--*the way you want it*.

Python 3 version.
%endif

%prep
%autosetup -n %{pypi_name}-%{version}

%build
%py2_build
%if 0%{?with_python3}
%py3_build
%endif

%install
%py2_install
%if 0%{?with_python3}
%py3_install
%endif

%check
py.test-%{python2_version} -v
%if 0%{?with_python3}
py.test-%{python3_version} -v
%endif

%files -n python2-%{pypi_name}
%license LICENSE-MIT
%doc README.rst
%{python2_sitelib}/%{pypi_name}-*.egg-info/
%{python2_sitelib}/%{pypi_name}.py*

%if 0%{?with_python3}
%files -n python3-%{pypi_name}
%license LICENSE-MIT
%doc README.rst
%{python3_sitelib}/%{pypi_name}-*.egg-info/
%{python3_sitelib}/%{pypi_name}.py
%{python3_sitelib}/__pycache__/%{pypi_name}.*
%endif

%changelog
* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.2-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 0.6.2-4
- Rebuild for Python 3.6

* Fri Dec 16 2016 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.6.2-3
- Don't own __pycache__ directory in python3 subpackage
- Really run tests (setup.py test doesn't do anything)
- Drop copy-pasted Requires (RHBZ #1405639)
- Trivial cleanups

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.2-2
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Fri Feb 05 2016 Germano Massullo <germano.massullo@gmail.com> - 0.6.2-1
- Heavy edits to make spec file compliant to https://fedoraproject.org/wiki/Packaging:Python (package python-docopt did not provide a python2-docopt package in Fedora repositories)
- Removed egg files stuff since they are no longer present in upstream source file.
- 0.6.2 minor update

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.1-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Nov 10 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.1-7
- Rebuilt for https://fedoraproject.org/wiki/Changes/python3.5

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.1-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.6.1-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed May 28 2014 Kalev Lember <kalevlember@gmail.com> - 0.6.1-4
- Rebuilt for https://fedoraproject.org/wiki/Changes/Python_3.4

* Mon Feb 03 2014 Martin Sivak <msivak@redhat.com> - 0.6.1-3
- Fix a mistake in spec file that prevented the subpackage from
  being created for Python 3

* Fri Nov 15 2013 Martin Sivak <msivak@redhat.com> - 0.6.1-2
- Enable python3 package

* Mon Aug 19 2013 Martin Sivak <msivak@redhat.com> - 0.6.1-1
- Upstream version sync

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.5.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.5.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Mon Jan 14 2013 Martin Sivak <msivak@redhat.com> - 0.5.0-1
- Initial release

