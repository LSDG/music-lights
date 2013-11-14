#!/bin/env python
from __future__ import print_function
import atexit
from itertools import cycle
from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys
import time
from random import choice

try:
    import gobject
except ImportError:
    pass

import ansi

from ConfigParserDefault import ConfigParserDefault
import mainLoop
from sampleGen import SampleGen


gcp = ConfigParserDefault()
gcp.read('config.ini')

usePygame = gcp.get_def('main', 'usePygame', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')
useSFML = gcp.get_def('main', 'useSFML', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')
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

songStart = None


if usePygame:
    import pygame_output
    SampleOutput = pygame_output.SampleOutput
    BaseProcess = pygame_output.PyGameProcess

elif useSFML:
    import pysfml_output
    SampleOutput = pysfml_output.SampleOutput
    BaseProcess = mainLoop.QueueHandlerProcess

else:
    import alsa_output
    SampleOutput = alsa_output.SampleOutput
    BaseProcess = alsa_output.ALSAProcess


class WebListener(BaseProcess):
    def __init__(self, controllerQueue, playerQueue):
        super(WebListener, self).__init__(controllerQueue)
        self.nextCommand = None
        self.playerQueue = playerQueue

    def onMessage(self, messageType, message):
        print('WebListener got message', message)
        self.nextCommand = (messageType, message)
        next(self.gen.filenameIter)

    def eachLoop(self):
        super(WebListener, self).eachLoop()
        global songStart
        # print('Looping!', songStart)

        if songStart is not None:
            if time.time() - songStart > 20:
                print('Time:', time.time(), songStart)
                self.playerQueue.put({'song': 'foobar'})
                songStart = time.time()


def CommandIterator(controller, fileList, controllerQueue):
    while True:
        if controller.nextCommand is not None:
            if 'play next' in controller.nextCommand[0]:
                print('CommandIterator got:', controller.nextCommand)
                global songStart
                songStart = time.time()
                nextThing = controller.nextCommand[1]
                controller.nextCommand = None
                yield nextThing
            elif 'stop' in controller.nextCommand[0]:
                raise StopIteration
            elif 'lost connection' in controller.nextCommand[0]:
                controller.nextCommand = None
                yield choice(fileList)
        else:
            print('CI get')
            controller.nextCommand = controllerQueue.get()


def runPlayerProcess(playerQueue, controllerQueue, fileList, nice=None, useCommandIterator=True):
    process = WebListener(controllerQueue, playerQueue)

    if useCommandIterator:
        files = CommandIterator(process, fileList, controllerQueue)
    else:
        files = cycle(files)

    sampleGen = SampleGen(files, gcp)
    sampleGen.onSongChanged.add(lambda *a, **kw: displayFileStarted(sampleGen))

    SampleOutput(sampleGen).play()

    SpectrumLightController(sampleGen)

    process.gen = sampleGen

    process.loop()


if __name__ == '__main__':
    runPlayerProcess(Queue(), Queue(), files)
