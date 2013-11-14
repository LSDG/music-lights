#!/usr/bin/env python
import os
import stat

import virtualenv


with open('installDeps.py', 'r') as installDepsFile:
    installDepsScript = installDepsFile.read()

with open('bootstrap.py', 'w') as bootstrap:
    # Write out the bootstrap script.
    bootstrap.write(virtualenv.create_bootstrap_script(installDepsScript))

    # Make the file executable.
    fileno = bootstrap.fileno()
    mode = os.fstat(fileno).st_mode
    os.fchmod(fileno, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
