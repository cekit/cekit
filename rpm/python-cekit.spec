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
Release:        1
Summary:        Container image creation tool
License:        MIT
URL:            https://github.com/cekit/cekit
Source0:        %{url}/archive/%{version}-%{release}.tar.gz
BuildArch:      noarch

%global _description \
Cekit helps to build container images from image definition files

%description %_description

%package -n python2-%{modname}
Summary:        %{summary}
Obsoletes:      python2-concreate
Provides:       python2-concreate
Conflicts:      python2-concreate
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
Requires:       PyYAML
Requires:       docker
Requires:       git
Requires:       bash-completion

%description -n python2-%{modname} %_description

Python 2 version.

%if 0%{?with_python3}
%package -n python3-%{modname}
Summary:        %{summary}
Obsoletes:      python3-concreate
Provides:       python3-concreate
Conflicts:      python3-concreate
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
Requires:       bash-completion

%description -n python3-%{modname} %_description

Python 3 version.
%endif

%prep
%setup -q -n %{modname}-%{version}-%{release}

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
mkdir -p %{buildroot}/%{_sysconfdir}/bash_completion.d
cp bash_completion/cekit %{buildroot}/%{_sysconfdir}/bash_completion.d/cekit
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
%{_sysconfdir}/bash_completion.d/cekit


%changelog
* Wed Jun 13 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-1
- 2.0 release

* Thu Jun 07 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.10.rc6
- rebuilt

* Wed Jun 06 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.9.rc5
- rebuilt

* Wed Jun 06 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.8.rc5
- rebuilt

* Wed Jun 06 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.7.rc5
- updated to rc5

* Thu May 24 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.6.rc4
- rebuilt

* Thu May 24 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.5.rc4
- rebuilt

* Thu May 24 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.4.rc4
- rebuilt

* Thu May 24 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.3.rc4
- rebuilt

* Mon May 21 2018 David Becvarik <dbecvari@redhat.com> - 2.0.0-0.2.rc3
- rebuilt

* Mon May 21 2018 David Becvarik <dbecvari@redhat.com> 2.0.0-0.1-rc3
- Release 2.0.0rc3

* Fri May 18 2018 David Becvarik <dbecvari@redhat.com> 2.0.0-0.1-rc2
- Release 2.0.0rc2

* Mon May 7 2018 David Becvarik <dbecvari@redhat.com> 2.0.0-0.1-rc1
- Release 2.0.0rc1

* Thu Mar 1 2018 David Becvarik <dbecvari@redhat.com> - 1.4.1-1
- Release 1.4.1

* Thu Dec 14 2017 David Becvarik <dbecvari@redhat.com> - 1.4.0-1
- Release 1.4.0

* Thu Dec 14 2017 David Becvarik <dbecvari@redhat.com> - 1.3.4-1
- Release 1.3.4

* Wed Nov 29 2017 David Becvarik <dbecvari@redhat.com> - 1.3.3-1
- Release 1.3.3

* Tue Nov 28 2017 David Becvarik <dbecvari@redhat.com> - 1.3.1-1
- Release 1.3.2

* Wed Nov 15 2017 David Becvarik <dbecvari@redhat.com> - 1.3.0-1
- Release 1.3.0

* Fri Oct 13 2017 Marek Goldmann <mgoldman@redhat.com> - 1.2.1-1
- Release 1.2.1

* Thu Oct 12 2017 Marek Goldmann <mgoldman@redhat.com> - 1.2.0-1
- Release 1.2.0

* Thu Oct 05 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.7-1
- Release 1.1.7

* Wed Oct 04 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.6-1
- Release 1.1.6

* Wed Oct 04 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.5-1
- Release 1.1.5

* Tue Oct 03 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.4-1
- Release 1.1.4

* Tue Oct 03 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.3-1
- Release 1.1.3

* Tue Oct 03 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.2-1
- Rebuilt

* Mon Oct 02 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.1-1
- Release 1.1.1

* Mon Oct 02 2017 Marek Goldmann <mgoldman@redhat.com> - 1.1.0-1
- Release 1.1.0

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

