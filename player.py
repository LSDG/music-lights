#!/bin/env python
from __future__ import print_function
import atexit
import ConfigParser
import collections
from itertools import cycle
from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys

import audioread

import pygame
import pygame.locals

import ansi


DONE_PLAYING_CHUNK = pygame.locals.USEREVENT

STOP = 0
CONTINUE = 1


gcp = ConfigParser.SafeConfigParser()
gcp.read('config.ini')

bytes_per_frame_per_channel = int(gcp.get('main', 'bytes_per_frame_per_channel', 2))

lightProcessNice = int(gcp.get('main', 'lightProcessNice', 0))
soundProcessNice = int(gcp.get('main', 'soundProcessNice', 0))

files = sys.argv[1:]

queuedCallbacks = collections.deque()
eventHandlers = dict()


if soundProcessNice:
    os.nice(soundProcessNice)

# Initialize pygame.mixer
pygame.mixer.pre_init(frequency=44100)
pygame.init()


class SampleGen(object):
    def __init__(self, filenames, **kwargs):
        self.framesPerChunk = kwargs.get('framesPerChunk', 4096)

        self.onSongChanged = set()
        self.onStopped = set()
        self.onSample = set()

        self.totalFramesRead = 0.0
        self.filenameIter = iter(filenames)
        self.currentData = None
        self.sampleIter = None

    def _loadNextFile(self):
        self.currentFilename = next(self.filenameIter)

        queuedCallbacks.extend(self.onSongChanged)

        self.file = audioread.audio_open(self.currentFilename)

        blockSize = self.framesPerChunk * self.file.channels * bytes_per_frame_per_channel
        try:
            # MAD (pymad)
            self.sampleIter = self.file.read_blocks(blockSize)
        except AttributeError:
            try:
                # FFMpeg (command line)
                self.sampleIter = self.file.read_data(blockSize)
            except AttributeError:
                # gstreamer (pygst)
                self.sampleIter = iter(self.file)

    @property
    def elapsedTime(self):
        return self.totalFramesRead / self.file.samplerate

    @property
    def channels(self):
        return self.file.channels

    @property
    def samplerate(self):
        return self.file.samplerate

    @property
    def duration(self):
        return self.file.duration

    def nextChunk(self):
        if self.sampleIter is None:
            self._loadNextFile()

        try:
            self.currentData = next(self.sampleIter)
        except (StopIteration, AttributeError):
            # Either we haven't loaded a song yet, or the one we were playing ended. Load another.
            self._loadNextFile()
            self.currentData = next(self.sampleIter)

        self.totalFramesRead += self.framesPerChunk

        queuedCallbacks.extend(self.onSample)

        return pygame.mixer.Sound(buffer(self.currentData))

    def close(self):
        # Stop stream.
        self.file.close()


class SpectrumLightController(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        sampleGen.onSample.add(self._onSample)
        sampleGen.onSongChanged.add(self._onSongChanged)

        atexit.register(self._onExit)

        self.messageQueue = Queue()

        self.process = Process(target=self.lightControllerProcess, args=(self.messageQueue, ))
        self.process.start()

    def _onSongChanged(self):
        try:
            self.messageQueue.put_nowait(('songChange', self.sampleGen.currentFilename))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onSample(self):
        try:
            self.messageQueue.put_nowait(('chunk', self.sampleGen.currentData))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onExit(self):
        if self.process.is_alive():
            try:
                self.messageQueue.put(('end', ))
            except QueueFull:
                ansi.error("Message queue to light process full! Continuing...")

    @staticmethod
    def lightControllerProcess(messageQueue):
        import lights

        if lightProcessNice:
            os.nice(lightProcessNice)

        analyzer = lights.SpectrumAnalyzer(messageQueue, gcp)
        analyzer.loop()


class SampleOutput(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        self.channel = pygame.mixer.Channel(0)
        self.channel.set_endevent(DONE_PLAYING_CHUNK)

        self.queueNextSound()  # Start playing the first chunk.
        self.queueNextSound()  # Queue the next chunk.

        eventHandlers[DONE_PLAYING_CHUNK] = self.queueNextSound

    def queueNextSound(self, event=None):
        chunk = sampleGen.nextChunk()
        chunk.play()

        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=sampleGen,
                suppressNewline=True
                )


def displayFileStarted():
    print()
    ansi.stdout(
            "Playing audio file: {style.fg.blue}{file.currentFilename}{style.none}\n"
                "{style.bold.fg.black}channels:{style.none} {file.channels}"
                "   {style.bold.fg.black}sample rate:{style.none} {file.samplerate} Hz"
                "   {style.bold.fg.black}duration:{style.none} {file.duration} s",
            file=sampleGen
            )


sampleGen = SampleGen(cycle(files))
sampleGen.onSongChanged.add(displayFileStarted)

output = SampleOutput(sampleGen)

lights = SpectrumLightController(sampleGen)


class QuitApplication(Exception):
    pass


def quitApp(event):
    raise QuitApplication

eventHandlers[pygame.locals.QUIT] = quitApp


def unhandledEvent(event):
    ansi.warn("Unhandled event! {!r}", event)


def processEvent(event):
    if event.type == pygame.locals.NOEVENT:
        return

    handler = eventHandlers.get(event.type, unhandledEvent)
    handler(event)


# Wait for stream to finish.
try:
    while True:
        processEvent(pygame.event.wait())

        # Process any queued callbacks.
        while queuedCallbacks:
            callback = queuedCallbacks.popleft()
            callback()

            # Process waiting events before moving on to the next callback.
            for event in pygame.event.get():
                processEvent(event)

except QuitApplication:
    print()
    print("Exiting application.")

except KeyboardInterrupt:
    print()
    print("User interrupted; exiting.")

ansi.info("Shutting down...")

pygame.quit()

ansi.done()
