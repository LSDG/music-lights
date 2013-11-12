#!/bin/env python
from __future__ import print_function
import atexit
from ConfigParserDefault import ConfigParserDefault
from itertools import cycle
from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys

try:
    import gobject
except ImportError:
    pass

import ansi

import mainLoop
from sampleGen import SampleGen


gcp = ConfigParserDefault()
gcp.read('config.ini')

usePygame = gcp.get_def('main', 'usePygame', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')
useGPIO = gcp.get_def('main', 'useGPIO', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')
lightProcessNice = int(gcp.get_def('main', 'lightProcessNice', 0))
soundProcessNice = int(gcp.get_def('main', 'soundProcessNice', 0))

files = sys.argv[1:]


if soundProcessNice:
    os.nice(soundProcessNice)


class SpectrumLightController(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        sampleGen.onSample.add(self._onSample)
        sampleGen.onSongChanged.add(self._onSongChanged)

        atexit.register(self._onExit)

        if useGPIO:
            import lights_gpio as lights
        else:
            import lights

        self.messageQueue = Queue()

        self.subProcess = Process(target=lights.runLightsProcess, args=(self.messageQueue, ))
        self.subProcess.start()

    def _onSongChanged(self, tags, songInfo):
        try:
            self.messageQueue.put_nowait(('songChange', self.sampleGen.currentFilename, songInfo))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onSample(self, data):
        try:
            if isinstance(data, buffer):
                data = bytes(data)
            self.messageQueue.put_nowait(('chunk', data))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onExit(self):
        if self.subProcess.is_alive():
            try:
                self.messageQueue.put(('end', ))
            except QueueFull:
                ansi.error("Message queue to light process full! Continuing...")


def displayFileStarted(sampleGen):
    print()
    ansi.stdout(
            "Playing audio file: {style.fg.blue}{file.currentFilename}{style.none}\n"
                "{style.bold.fg.black}channels:{style.none} {file.channels}"
                "   {style.bold.fg.black}sample rate:{style.none} {file.samplerate} Hz"
                "   {style.bold.fg.black}duration:{style.none} {file.duration} s",
            file=sampleGen
            )


def runPlayerProcess(playerQueue, controllerQueue, nice=None):
    if usePygame:
        from pygame_output import SampleOutput
        process = pygame_output.PyGameProcess(controllerQueue)

    else:
        from pysfml_output import SampleOutput
        process = mainLoop.QueueHandlerProcess(controllerQueue)

    sampleGen = SampleGen(cycle(files), gcp)
    sampleGen.onSongChanged.add(lambda *a: displayFileStarted(sampleGen))

    SampleOutput(sampleGen).play()

    SpectrumLightController(sampleGen)

    process.loop()


if __name__ == '__main__':
    runPlayerProcess(Queue(), Queue())
