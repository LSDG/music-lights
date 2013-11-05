#!/usr/bin/env python
import os
import stat

import virtualenv


requiredPackages = """
pyFFTW
audioread
hsaudiotag
numpy
pygame
pyserial
""".split()


installDepsScript = """
import subprocess

def after_install(options, virt_env_dir):
    requiredPackages = {!r}
    subprocess.call([join(virt_env_dir, 'bin', 'easy_install')] + requiredPackages)

def adjust_options(options, args):
    if len(args) == 0:
        args.append('virtenv')
""".format(requiredPackages)

with open('bootstrap.py', 'w') as bootstrap:
    # Write out the bootstrap script.
    bootstrap.write(virtualenv.create_bootstrap_script(installDepsScript))

    # Make the file executable.
    fileno = bootstrap.fileno()
    mode = os.fstat(fileno).st_mode
    os.fchmod(fileno, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
