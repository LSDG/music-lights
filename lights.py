from __future__ import print_function
import ConfigParser
import datetime
import os
from weakref import ref

from numpy import array_split, short, fromstring
from numpy.random import rand as rand_array

import anfft

import RPi.GPIO as GPIO


pins = [0, 1, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 21, 22, 23, 24, 25]

# Warm up ANFFT, allowing it to determine which FFT algorithm will work fastest on this machine.
anfft.fft(rand_array(1024), measure=True)


class SpectrumAnalyzer(object):
    def __init__(self, messageQueue, config):
        self.messageQueue = messageQueue
        self._dataSinceLastSpectrum = []

        self.loadSettings(config)

        self.lights = LightController(self, config)

    def loadSettings(self, gcp):
        # The number of spectrum analyzer bands (also light output channels) to use.
        self.frequencyBands = int(gcp.get('main', 'frequencyBands', 16))

        self.bytes_per_frame_per_channel = int(gcp.get('main', 'bytes_per_frame_per_channel', 2))

    def _onChunk(self, data):
        self._currentSpectrum = None
        self._dataSinceLastSpectrum.append(data)

        self.lights._onChunk()

    @property
    def spectrum(self):
        if self._currentSpectrum is None:
            dataArr = fromstring(''.join(self._dataSinceLastSpectrum), dtype=short)
            normalized = dataArr / float(2 ** (self.bytes_per_frame_per_channel * 8))

            # Cut the spectrum down to the appropriate number of bands.
            bands = array_split(abs(anfft.rfft(normalized)), self.frequencyBands)

            self._currentSpectrum = map((lambda arr: sum(arr) / len(arr)), bands)

            self._dataSinceLastSpectrum = []

        return self._currentSpectrum

    def loop(self):
        while True:
            message = self.messageQueue.get(timeout=60)
            messageType = message[0]

            if messageType == 'songChange':
                self.lights._onSongChanged(*message[1:])

            elif messageType == 'chunk':
                self._onChunk(*message[1:])

            elif messageType == 'end':
                break


class LightController(object):
    def __init__(self, analyzer, config):
        self.analyzer = ref(analyzer)
        self.lastLightUpdate = datetime.datetime.now()

        self.loadSettings(config)

        self.frequencyThresholds = self.defaultThresholds
        self.frequencyBandOrder = self.defaultOrder

        GPIO.setmode(GPIO.BCM)
        for pin in pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)

        self.previousLightStates = [False] * analyzer.frequencyBands

    def loadSettings(self, gcp):
        # Slow the light state changes down to every 0.05 seconds.
        self.delayBetweenUpdates = float(gcp.get('main', 'delayBetweenUpdates', 0.05))

        self.defaultThresholds = map(float, gcp.get('spectrum', 'thresholds').split(','))
        self.defaultOrder = map(int, gcp.get('spectrum', 'channelOrder').split(','))

    def _onSongChanged(self, filename):
        self.frequencyThresholds = self.defaultThresholds
        self.frequencyBandOrder = self.defaultOrder

        iniPath = filename + '.ini'
        if os.path.exists(iniPath):
            cp = ConfigParser.SafeConfigParser()
            cp.read([iniPath])

            self.frequencyThresholds = map(float, cp.get('spectrum', 'thresholds').split(','))
            self.frequencyBandOrder = map(int, cp.get('spectrum', 'channelOrder').split(','))

    def _onChunk(self):
        now = datetime.datetime.now()
        if (now - self.lastLightUpdate).total_seconds() > self.delayBetweenUpdates:
            self.lastLightUpdate = now

            spectrum = self.analyzer().spectrum
            bands = [spectrum[i] for i in self.frequencyBandOrder]
            lightStates = [level > self.frequencyThresholds[channel] for channel, level in enumerate(bands)]

            for channel, value in enumerate(lightStates):
                if self.previousLightStates[channel] != value:
                    GPIO.output(pins[channel], value)

            self.previousLightStates = lightStates
