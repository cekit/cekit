%if 0%{?rhel}
%global with_python3 0
%else
%global with_python3 1
%endif

%global modname colorlog

Name:           python-colorlog
Version:        3.1.0
Release:        2%{?dist}
Summary:        Log formatting with colors!
License:        MIT
URL:            https://github.com/borntyping/python-colorlog
Source0:        %{url}/archive/v%{version}.tar.gz
BuildArch:      noarch

%global _description \
Log formatting with colors!

%description %_description

%package -n python2-%{modname}
Summary:        %{summary}

BuildRequires:  python2-devel
BuildRequires:  python2-setuptools

%description -n python2-%{modname} %_description

Python 2 version.

%if 0%{?with_python3}
%package -n python3-%{modname}
Summary:        %{summary}

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

%description -n python3-%{modname} %_description

Python 3 version.
%endif

%prep
%setup -n %{name}-%{version}

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

%files -n python2-%{modname}
%doc README.md
%license LICENSE
%{python2_sitelib}/colorlog/
%{python2_sitelib}/colorlog-*.egg-info/

%if 0%{?with_python3}
%files -n python3-%{modname}
%doc README.md
%license LICENSE
%{python3_sitelib}/colorlog/
%{python3_sitelib}/colorlog-*.egg-info/
%endif

%changelog
* Mon Sep 25 2017 Marek Goldmann <mgoldman@redhat.com> - 3.1.0-2
- Rebuild

* Thu Sep 21 2017 Marek Goldmann <mgoldman@redhat.com> - 3.1.0-1
- Initial release

