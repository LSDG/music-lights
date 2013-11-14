import importlib
import os
from os.path import basename, dirname, join
import subprocess
import sys


requiredPackages = {
        'audioread': 'audioread',
        'hsaudiotag': 'hsaudiotag',
        'numpy': 'numpy',
        'pyFFTW': 'pyfftw',
        'pyalsaaudio': 'alsaaudio',
        'pyserial': 'serial',
        }

packageFilesToLink = []
packagesToInstall = []

for pkg, mod in requiredPackages.items():
    try:
        modPath = importlib.import_module(mod).__file__
        packageFilesToLink.append(modPath)
        print("Package {!r} already installed; symlinking.".format(pkg))

    except ImportError:
        packagesToInstall.append(pkg)
        print("Package {!r} not installed; installing.".format(pkg))


def after_install(options, virt_env_dir):
    # Symlink packages that are already installed on the system.
    py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])
    site_packages_dir = join(virt_env_dir, 'lib', py_version)

    for path in packageFilesToLink:
        while not basename(dirname(path)).endswith('-packages') and not basename(dirname(path)).startswith('python'):
            path = dirname(path)

        try:
            os.symlink(path, join(site_packages_dir, basename(path)))
        except Exception:
            import traceback
            print("Error symlinking {!r} into {!r}:".format(path, site_packages_dir))
            traceback.print_exc()
            sys.exit(1)

    # Install remaining packages
    subprocess.call([join(virt_env_dir, 'bin', 'easy_install')] + packagesToInstall)


def adjust_options(options, args):
    if len(args) == 0:
        args.append('virtenv')
