%if 0%{?rhel}
%global with_python3 0
%else
%global with_python3 1
%endif

%global modname cekit

Name:           python-cekit
Version:        2.0.0
Obsoletes:      python-concreate
Provides:       python-concreate
Conflicts:      python-concreate
Release:        0.1.git%{?dist}
Summary:        Container image creation tool
License:        MIT
URL:            https://github.com/cekit/cekit
Source0:        %{url}/archive/%{version}.tar.gz
BuildArch:      noarch

%global _description \
Cekit helps to build container images from image definition files

%description %_description

%package -n python2-%{modname}
Summary:        %{summary}

BuildRequires:  python2-devel
BuildRequires:  python2-setuptools
BuildRequires:  python2-mock
BuildRequires:  python2-pykwalify
BuildRequires:  PyYAML
BuildRequires:  python2-colorlog
BuildRequires:  python-jinja2

%if 0%{?rhel}
BuildRequires:  pytest
Requires:       python-jinja2
Requires:       python-setuptools
%else
BuildRequires:  python2-pytest
Requires:       python2-jinja2
Requires:       python2-setuptools
%endif

Requires:       python2-pykwalify
Requires:       python2-colorlog
Requires:       python2-future
Requires:       PyYAML
Requires:       docker
Requires:       git

%description -n python2-%{modname} %_description

Python 2 version.

%if 0%{?with_python3}
%package -n python3-%{modname}
Summary:        %{summary}

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pytest
BuildRequires:  python3-mock
BuildRequires:  PyYAML
BuildRequires:  python3-pykwalify
BuildRequires:  python3-colorlog
BuildRequires:  python3-jinja2
Requires:       PyYAML
Requires:       docker
Requires:       python3-pykwalify
Requires:       python3-colorlog
Requires:       python3-jinja2
Requires:       python3-setuptools
Requires:       git

%description -n python3-%{modname} %_description

Python 3 version.
%endif

%prep
%setup -q -n %{modname}-%{git_version}

%build
%py2_build
%if 0%{?with_python3}
%py3_build
%endif

#%check
#py.test-%{python2_version} -v tests/test_unit*.py
#%if 0%{?with_python3}
#py.test-%{python3_version} -v tests/test_unit*.py
#%endif

%install
%py2_install
%if 0%{?with_python3}
%py3_install
%endif

%files -n python2-%{modname}
%doc README.rst
%license LICENSE
%{python2_sitelib}/cekit/
%{python2_sitelib}/cekit-*.egg-info/

%if 0%{?with_python3}
%files -n python3-%{modname}
%doc README.rst
%license LICENSE
%{python3_sitelib}/cekit/
%{python3_sitelib}/cekit-*.egg-info/
%endif

# This file ends up in py3 subpackage if enabled, otherwise in py2
%{_bindir}/concreate
%{_bindir}/cekit

%changelog


* Fri Sep 29 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.0-0.3.git
- Rebuild

* Fri Sep 29 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.0-0.2.git
- Rebuild

* Thu Sep 28 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.0-0.1.git
- Switch to latest release from develop branch

* Wed Sep 27 2017 Marek Goldmann <mgoldman@redhat.com> - 1.0.0-6
- Updated deps

* Tue Sep 26 2017 Marek Goldmann <mgoldman@redhat.com> - 1.0.0-5
- Updated six depenencies

* Mon Sep 25 2017 Marek Goldmann <mgoldman@redhat.com> - 1.0.0-4
- Rebuild

* Mon Sep 25 2017 Marek Goldmann <mgoldman@redhat.com> - 1.0.0-3
- Cleanup in dependencies

* Mon Sep 25 2017 Marek Goldmann <mgoldman@redhat.com> - 1.0.0-2
- Rebuild

* Thu Sep 21 2017 Marek Goldmann <mgoldman@redhat.com> - 1.0.0-1
- Initial release

