#!/bin/env python
from __future__ import print_function
import ConfigParser
import collections
import datetime
from itertools import cycle
from multiprocessing import Process, Queue
import os
import sys

from numpy import array_split, short, fromstring
from numpy.random import rand as rand_array

import anfft

import audioread

import pygame
import pygame.locals

import ansi


pins = [0, 1, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 21, 22, 23, 24, 25]

DONE_PLAYING_CHUNK = pygame.locals.USEREVENT

STOP = 0
CONTINUE = 1


def launchProc(messageQueue):
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)

    while True:
        msg = messageQueue.get(True)

        if msg == 'end':
            break

        for channel, value in enumerate(msg):
            GPIO.output(pins[channel], value)

messageQueue = Queue()
p = Process(target=launchProc, args=(messageQueue, ))
p.start()

gcp = ConfigParser.SafeConfigParser()
gcp.read('config.ini')


# The number of spectrum analyzer bands (also light output channels) to use.
frequencyBands = int(gcp.get('main', 'frequencyBands', 16))

# Slow the light state changes down to every 0.05 seconds.
delayBetweenUpdates = float(gcp.get('main', 'delayBetweenUpdates', 0.05))

bytes_per_frame_per_channel = int(gcp.get('main', 'bytes_per_frame_per_channel', 2))

defaultThresholds = map(float, gcp.get('spectrum', 'thresholds').split(','))
defaultOrder = map(int, gcp.get('spectrum', 'channelOrder').split(','))


files = sys.argv[1:]


# Initialize pygame.mixer
pygame.mixer.pre_init(frequency=44100)
pygame.init()

# Warm up ANFFT, allowing it to determine which FFT algorithm will work fastest on this machine.
anfft.fft(rand_array(1024), measure=True)


queuedCallbacks = collections.deque()
eventHandlers = dict()


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
        self._dataSinceLastSpectrum = []

    def _loadNextFile(self):
        self.currentFilename = next(self.filenameIter)

        queuedCallbacks.extend(self.onSongChanged)

        self.file = audioread.audio_open(self.currentFilename)
        self.sampleIter = self.file.read_data(self.framesPerChunk * self.file.channels * bytes_per_frame_per_channel)

    @property
    def spectrum(self):
        if self._currentSpectrum is None:
            dataArr = fromstring(self.currentData, dtype=short)
            normalized = dataArr / float(2 ** (bytes_per_frame_per_channel * 8))

            # Cut the spectrum down to the appropriate number of bands.
            bands = array_split(abs(anfft.rfft(normalized)), frequencyBands)

            self._currentSpectrum = map((lambda arr: sum(arr) / len(arr)), bands)

            self._dataSinceLastSpectrum = []

        return self._currentSpectrum

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

        self.currentData = buffer(next(self.sampleIter))
        #FIXME: Detect end of song, and call self._loadNextFile()!

        self.totalFramesRead += self.framesPerChunk
        self._currentSpectrum = None
        self._dataSinceLastSpectrum.append(self.currentData)

        queuedCallbacks.extend(self.onSample)

        return pygame.mixer.Sound(self.currentData)

    def close(self):
        # Stop stream.
        self.fFile.close()


class SpectrumLightController(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen
        self.lastLightUpdate = datetime.datetime.now()

        sampleGen.onSample.add(self._onSample)
        sampleGen.onSongChanged.add(self._onSongChanged)

    def _onSongChanged(self):
        self.frequencyThresholds = defaultThresholds
        self.frequencyBandOrder = defaultOrder

        iniPath = self.currentFilename + '.ini'
        if os.path.exists(iniPath):
            cp = ConfigParser.SafeConfigParser()
            cp.read([iniPath])
            self.frequencyThresholds = map(float, cp.get('spectrum', 'thresholds').split(','))
            self.frequencyBandOrder = map(int, cp.get('spectrum', 'channelOrder').split(','))

    def _onSample(self):
        now = datetime.datetime.now()
        if (now - self.lastLightUpdate).total_seconds() > delayBetweenUpdates:
            self.lastLightUpdate = now

            spectrum = self.sampleGen.spectrum
            bands = [spectrum[i] for i in self.frequencyBandOrder]
            lightStates = [level > self.frequencyThresholds[channel] for channel, level in enumerate(bands)]

            messageQueue.put(lightStates)


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

messageQueue.put('end')
pygame.quit()

ansi.done()
