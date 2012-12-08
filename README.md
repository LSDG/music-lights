LSDG Music-Activated Lights
===========================

Prerequisites
-------------

- [Python](http://www.python.org/) 2.6 or newer
- [virtualenv](http://www.virtualenv.org/en/latest/)
- [PortAudio](http://www.portaudio.com/)
- [libusb](http://www.libusb.org/) with development headers (`libusb-dev` in Debian/Ubuntu)


Getting Started
---------------

After installing the prerequisites above, use `bootstrap.py` to create a virtual Python environment in `virtenv`:

	python bootstrap.py

Next, you will need to build the MSP430 (Launchpad) support library `msplib`:

	virtenv/bin/pip install ./msplib

Once that has completed successfully, you can run the project:

	virtenv/bin/python player.py


Acknowledgements
----------------

Apologies to Daniel Beer, the author of [mspdebug](http://mspdebug.sourceforge.net/), for hacking the crap out of his
project. `msplib` is actually just a Python wrapper around a stripped-down version of the `mspdebug` source, with most
features ripped out in order to get something which worked for our use case. Hopefully it won't last long in its
current form, and will instead become a more generally-usable library for interfacing with the MSP430 from Python.
