%global distroname Mer

Summary: The skeleton package which defines a simple %{distroname} system
Name: basesystem
Version:    11+git1
Release: 1
License: Public Domain
Group: System Environment/Base
Requires(pre): setup filesystem
BuildArch: noarch
Source: %{name}-%{version}.tar.bz2

%description
Basesystem defines the components of a basic %{distroname} system 
(for example, the package installation order to use during bootstrapping).
Basesystem should be in every installation of a system, and it
should never be removed.

%prep

%build

%install

%clean

%files
%defattr(-,root,root,-)
