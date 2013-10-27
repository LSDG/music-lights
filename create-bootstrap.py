#!/usr/bin/env python
import os
import stat
import textwrap

import virtualenv


requiredPackages = """
anfft
audioread
hsaudiotag
numpy
pygame
RPi.GPIO
""".split()


output = virtualenv.create_bootstrap_script(textwrap.dedent("""
import subprocess

def after_install(options, virt_env_dir):
    requiredPackages = {!r}
    subprocess.call([join(virt_env_dir, 'bin', 'pip'), 'install'] + requiredPackages)

def adjust_options(options, args):
    if len(args) == 0:
        args.append('virtenv')
""").format(requiredPackages))

with open('bootstrap.py', 'w') as bootstrap:
    # Write out the bootstrap script.
    bootstrap.write(output)

    # Make the file executable.
    fileno = bootstrap.fileno()
    mode = os.fstat(fileno).st_mode
    os.fchmod(fileno, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
