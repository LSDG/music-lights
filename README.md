LSDG Music-Activated Lights
===========================

Prerequisites
-------------

- [Python](http://www.python.org/) 2.6 or newer
- [virtualenv](http://www.virtualenv.org/en/latest/)
- [PyGame](http://www.pygame.org/)
- [FFmpeg](http://ffmpeg.org/)
   (or [MAD](http://www.underbit.com/products/mad/); or, in a pinch, [gstreamer](http://gstreamer.freedesktop.org/))


Getting Started
---------------

After installing the prerequisites above, use `bootstrap.py` to create a virtual Python environment in `virtenv`:

	python bootstrap.py

Once that has completed successfully, you can run the project:

	virtenv/bin/python player.py
