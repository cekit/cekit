%global pname pykwalify

%if 0%{?rhel}
%global default_python 2
%else
%global with_python3 1
%global default_python 3
%endif

Name:           python-%{pname}
Version:        1.6.0
Release:        4%{?dist}
Summary:        Python lib/cli for JSON/YAML schema validation

License:        MIT
URL:            https://github.com/grokzen/pykwalify
Source0:        %{url}/archive/%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools

%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
%endif

%description
It is a YAML/JSON validation library.
This framework is a port with a lot added functionality
of the java version of the framework kwalify that can be
found at: http://www.kuwata-lab.com/kwalify/


%package -n     python2-%{pname}
Summary:        Python lib/cli for JSON/YAML schema validation
%{?python_provide:%python_provide python2-%{pname}}

Requires:       python-docopt
Requires:       PyYAML
Requires:       python-dateutil
Requires:       python-setuptools

%description -n python2-%{pname}
It is a YAML/JSON validation library.
This framework is a port with a lot added functionality
of the java version of the framework kwalify that can be
found at: http://www.kuwata-lab.com/kwalify/

%if 0%{?with_python3}
%package -n     python3-%{pname}
Summary:        Python lib/cli for JSON/YAML schema validation
%{?python_provide:%python_provide python3-%{pname}}

Requires:       python3-docopt
Requires:       python3-PyYAML
Requires:       python3-dateutil
Requires:       python3-setuptools

%description -n python3-%{pname}
It is a YAML/JSON validation library.
This framework is a port with a lot added functionality
of the java version of the framework kwalify that can be
found at: http://www.kuwata-lab.com/kwalify/
%endif

%prep
%autosetup -n %{pname}-%{version}
rm -rf *.egg-info

sed -i "s|^PyYAML.*|PyYAML|g" requirements.txt
sed -i "s|PyYAML.*|PyYAML',|g" setup.py
sed -i "s|^python-dateutil.*|python-dateutil|g" requirements.txt
sed -i "s|python-dateutil.*|python-dateutil',|g" setup.py

%build
%py2_build

%if 0%{?with_python3}
%py3_build
%endif

%install
%py2_install
mv %{buildroot}%{_bindir}/%{pname} %{buildroot}%{_bindir}/python2-%{pname}

%if 0%{?with_python3}
%py3_install
mv %{buildroot}%{_bindir}/%{pname} %{buildroot}%{_bindir}/python3-%{pname}
%endif

%if 0%{?default_python} >= 3
ln -s %{_bindir}/python3-%{pname} %{buildroot}%{_bindir}/%{pname}
%else
ln -s %{_bindir}/python2-%{pname} %{buildroot}%{_bindir}/%{pname}
%endif


%files -n python2-%{pname}
%doc README.md
%if 0%{?default_python} <= 2
%{_bindir}/%{pname}
%endif
%{_bindir}/python2-%{pname}
%{python2_sitelib}/%{pname}
%{python2_sitelib}/%{pname}-%{version}-py?.?.egg-info

%if 0%{?with_python3}
%files -n python3-%{pname}
%doc README.md
%if 0%{?default_python} >= 3
%{_bindir}/%{pname}
%endif
%{_bindir}/python3-%{pname}
%{python3_sitelib}/%{pname}
%{python3_sitelib}/%{pname}-%{version}-py?.?.egg-info
%endif

%changelog
* Fri Sep 29 2017 Marek Goldmann <mgoldman@redhat.com> - 1.6.0-4
- Rebuild

* Fri Sep 29 2017 Marek Goldmann <mgoldman@redhat.com> - 1.6.0-3
- Rebuild

* Mon Sep 25 2017 Marek Goldmann <mgoldman@redhat.com> - 1.6.0-2
- Rebuild

* Thu Sep 21 2017 Marek Goldmann <mgoldman@redhat.com> - 1.6.0-1
- Update to 1.6.0

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.5.1-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.5.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 1.5.1-3
- Rebuild for Python 3.6

* Mon Oct 17 2016 Chandan Kumar <chkumar@redhat.com> - 1.5.1-2
- Removed versions of BR
- Removed unnecessary files

* Thu Oct 13 2016 Chandan Kumar <chkumar@redhat.com> - 1.5.1-1
- Initial package.
