%global py_ver %(%{__python3} -c 'import sys; print(sys.version[:3])')
%define py_libdir %{_libdir}/python%{py_ver}

# The base directory (almost chroot) for rpmlint-mini
# This has to be /opt/testing for obs-build to find /opt/testing/bin/rpmlint
%define sa_base /opt/testing

Name:           rpmlint-mini
BuildRequires:  glib2-devel glib2-static pkgconfig rpm-python rpmlint
# These are the packages that rpmlint pulls in and need to be included into this standalone package
%define rpmlint_requires rpmlint python3-magic python3-toml python3-xdg python3-setuptools rpm-python
# python3-enchant is not yet packaged and is dynamically loaded
BuildRequires:  python3-devel
BuildRequires:  python3-magic
BuildRequires:  libtool
Summary:        Rpm correctness checker
Version:        1.12pre+git1
Release:        1
Url:            http://rpmlint.zarb.org/
License:        GPLv2+
Source:         desktop-file-utils-0.17.tar.bz2
Patch10:        static-desktop-file-validate.diff
# Not using macro as check_package_is_complete failed when using py_ver macro here
Source100:      rpmlint-deps-3.8.txt
Source101:      rpmlint.wrapper
# Config
Source200:      rpmlint-mini-rpmlintrc
Source201:      polkit-default-privs.config
# Test assets:  Our spec file and a tiny rpm
Source300:      basesystem.spec
Source301:      basesystem-11+git1-1.3.65.jolla.noarch.rpm
Source302:      basesystem-rpmlintrc
# Readme
Source400:      README.jolla


%description
rpmlint-mini is a self-contained and minimal re-package of rpmlint,
python3 and required python modules with minimal requirements.
Rpmlint is a tool to check common errors on rpm packages. Binary and
source packages can be checked.

%prep
%setup -q -n desktop-file-utils-0.17
%patch10

%build
autoreconf -fi
%configure
pushd src
make desktop-file-validate V=1
popd

%install
rm -rf $RPM_BUILD_ROOT
# test if the rpmlint works at all
set +e
# check installed rpmlint package
echo "Testing vanilla rpmlint is installed and runs correctly. If this fails then rpmlint is broken!"
/usr/bin/rpmlint -i rpmlint
test $? -gt 0 -a $? -lt 60 && exit 1
set -e

# okay, lets put it together in the standalone root:
%define sa_root %{buildroot}%{sa_base}

rm -rf %{sa_root}
mkdir -p %{sa_root}%{_bindir}
mkdir -p %{sa_root}/bin
mkdir -p %{sa_root}%{_libdir}
mkdir -p %{sa_root}%{_sysconfdir}/rpmlint
mkdir -p %{sa_root}%{_sysconfdir}/pythonstart


# Install our desktop-file-validate binary
install -m 755 -D src/desktop-file-validate %{sa_root}/usr/bin/desktop-file-validate

# Install config files
for i in "%{SOURCE200}" "%{SOURCE201}"; do
  cp $i %{sa_root}%{_sysconfdir}/rpmlint
done


# Setup a minimal python3
install -D %{_bindir}/python3 %{sa_root}/%{_bindir}/python3
cp -a %{_libdir}/libpython%{py_ver}.so* %{sa_root}/%{_libdir}
install -m 644 -D /usr/include/python%{py_ver}/pyconfig.h %{sa_root}/usr/include/python%{py_ver}/pyconfig.h

# These are the python modules and libraries needed by rpmlint etc
pushd %{py_libdir}
for f in $(<%{SOURCE100}); do
  find -path "*/$f" -exec install -D {} %{sa_root}/%{py_libdir}/{} \;
done
popd
# Follow the same approach as sb2-tools-template to setup rpmlint and dependencies
# Copy all files from the rpms that rpmlint requires into the sa_root
rpm -ql %{rpmlint_requires} > rpmlint.files
tar --no-recursion -T rpmlint.files -cpf - | ( cd %{sa_root} && tar -xvpf - ) > rpmlint.files_in_sa_root

# The rpmlint-mini wrapper will set LD_LIBRARY_PATH to sa_root/_libdir
# so we can add libraries in there.
# libmagic is part of 'file' and needed by python3-magic
cp -a %{_libdir}/libmagic.so.* %{sa_root}/%{_libdir}

# Now we byte-compile and optimise to compress
# Ues the 'legacy' pyc naming as per the PEP
# https://www.python.org/dev/peps/pep-3147/#case-4-legacy-pyc-files-and-source-less-imports
# so we can remove the .py files (this doesn't work with __pycache__/ dirs!)
pushd %{sa_root}/%{py_libdir}/
%{__python3} -O -m compileall -b .
find . -name \*py | xargs rm
popd

# Use the rpmlint-mini wrapper
mv %{sa_root}/%{_bindir}/rpmlint %{sa_root}/%{_bindir}/rpmlint.real
install -m 755 -D %{SOURCE101} %{sa_root}/%{_bindir}/rpmlint
ln -s ../%{_bindir}/rpmlint %{sa_root}/bin/rpmlint

# work around the rpmbuild require/provide
%define my_requires %{_builddir}/%{?buildsubdir}/%{name}-requires
cat << EOF > %my_requires
cat - > /tmp/file.list
%{__find_requires} < /tmp/file.list > /tmp/requires.list
%{__find_provides} < /tmp/file.list > /tmp/provides.list
while read i; do
    grep -F -v "\$i" /tmp/requires.list > /tmp/requires.list.new
    mv /tmp/requires.list.new /tmp/requires.list
done < /tmp/provides.list
cat /tmp/requires.list
rm -f /tmp/requires.list /tmp/provides.list /tmp/file.list
EOF
chmod +x %my_requires
%define _use_internal_dependency_generator 0
%define __find_requires %my_requires
%define __find_provides %nil

# Errors from here are hopefully down to things required by rpmlint and python3
echo Running standalone rpmlint to check for missing python imports libraries etc
# The rpmlint wrapper allows us to override the standalone root using $SA_ROOT
export SA_ROOT=%{sa_root}
# Check the wrapper runs with no Checks
%{sa_root}/bin/rpmlint --verbose --help || exit 1
# Now just run the Checks against a simple rpm and this spec file so
# we're not caught out when running real tests.  If anything fails due to
# missing imports then update rpmlint-deps*.txt
# First check spec file
%{sa_root}/bin/rpmlint --verbose %{SOURCE300} || exit 1
# And then a tiny test rpm
%{sa_root}/bin/rpmlint --verbose --rpmlintrc %{SOURCE302} %{SOURCE301} || exit 1

echo "ok.... standalone rpmlint-mini has run successfully"

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,0755)
%{sa_base}
