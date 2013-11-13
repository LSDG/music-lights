#!/bin/env python
from __future__ import print_function
import atexit
from ConfigParserDefault import ConfigParserDefault
from itertools import cycle
from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
from Queue import Empty
import sys
import time
from random import choice

import pygame
import pygame.locals

import ansi

import mainLoop
from sampleGen import SampleGen


DONE_PLAYING_CHUNK = pygame.locals.USEREVENT

STOP = 0
CONTINUE = 1


gcp = ConfigParserDefault()
gcp.read('config.ini')

lightProcessNice = int(gcp.get_def('main', 'lightProcessNice', 0))
soundProcessNice = int(gcp.get_def('main', 'soundProcessNice', 0))

files = sys.argv[1:]


if soundProcessNice:
    os.nice(soundProcessNice)

# Initialize pygame.mixer
pygame.mixer.pre_init(frequency=44100)
pygame.init()


class SpectrumLightController(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        sampleGen.onSample.add(self._onSample)
        sampleGen.onSongChanged.add(self._onSongChanged)

        atexit.register(self._onExit)

        self.messageQueue = Queue()

        import lights

        self.subProcess = Process(target=lights.runLightsProcess, args=(self.messageQueue, ))
        self.subProcess.start()

    def _onSongChanged(self, tags):
        try:
            self.messageQueue.put_nowait(('songChange', self.sampleGen.currentFilename))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onSample(self, data):
        try:
            self.messageQueue.put_nowait(('chunk', data))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onExit(self):
        if self.subProcess.is_alive():
            try:
                self.messageQueue.put(('end', ))
            except QueueFull:
                ansi.error("Message queue to light process full! Continuing...")


class SampleOutput(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        self.channel = pygame.mixer.Channel(0)
        self.channel.set_endevent(DONE_PLAYING_CHUNK)

        self.queueNextSound()  # Start playing the first chunk.
        self.queueNextSound()  # Queue the next chunk.

        mainLoop.currentProcess.eventHandlers[DONE_PLAYING_CHUNK] = self.queueNextSound

    def queueNextSound(self, event=None):
        chunk = self.sampleGen.nextChunkSound()
        chunk.play()

        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=self.sampleGen,
                suppressNewline=True
                )


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

class WebListener(mainLoop.PyGameProcess):
    def __init__(self, controllerQueue, playerQueue):
        super(WebListener, self).__init__(controllerQueue)
        self.nextCommand = None
        self.playerQueue = playerQueue

    def onMessage(self, messageType, message):
        print('WebListener got message', message)
        self.nextCommand = (messageType, message)

    def eachLoop(self):
        print('Looping!', songStart)

        if songStart is not None:
            print('Time:', time.time() - songStart)
            if time.time() - songStart > 120:
                self.playerQueue.put({'song': 'foobar'})

def CommandIterator(controller, fileList, controllerQueue):
    while True:
        if controller.nextCommand is not None:
            if 'play next' in controller.nextCommand:
                global songStart
                songStart = time.time()
                nextThing = controller.nextCommand['play next']
                controller.nextCommand = None
                yield nextThing
            elif 'stop' in controller.nextCommand:
                raise StopIteration
            elif 'lost connection' in controller.nextCommand[0]:
                controller.nextCommand = None
                yield choice(fileList)
        else:
            controller.nextCommand = controllerQueue.get()


def runPlayerProcess(playerQueue, controllerQueue, fileList, nice=None):
    print('before run')
    process = WebListener(controllerQueue, playerQueue)

    #sampleGen = SampleGen(cycle(files), gcp)
    sampleGen = SampleGen(CommandIterator(process, fileList, controllerQueue), gcp)
    sampleGen.onSongChanged.add(lambda: displayFileStarted(sampleGen))

    SampleOutput(sampleGen)
    SpectrumLightController(sampleGen)

    process.loop()


if __name__ == '__main__':
    runPlayerProcess(Queue(), Queue(), files)
