from __future__ import print_function
import ConfigParser
import datetime
import os
from weakref import ref

import RPi.GPIO as GPIO

from mainLoop import QueueHandlerProcess


pins = [0, 1, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 21, 22, 23, 24, 25]


class LightController(object):
    def __init__(self, analyzer, config):
        self.analyzer = ref(analyzer)
        self.lastLightUpdate = datetime.datetime.now()

        self.loadSettings(config)

        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

        GPIO.setmode(GPIO.BCM)
        for pin in pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)

        self.previousLightStates = [False] * analyzer.frequencyBands

    def loadSettings(self, config):
        # Slow the light state changes down to every 0.05 seconds.
        self.delayBetweenUpdates = float(config.get('main', 'delayBetweenUpdates', 0.05))

        self.defaultThresholds = map(float, config.get('spectrum', 'thresholds').split(','))
        self.defaultOffThresholds = map(float, config.get('spectrum', 'offThresholds').split(','))
        self.defaultOrder = map(int, config.get('spectrum', 'channelOrder').split(','))

    def _onSongChanged(self, filename):
        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

        iniPath = filename + '.ini'
        if os.path.exists(iniPath):
            cp = ConfigParser.SafeConfigParser()
            cp.read([iniPath])

            self.frequencyThresholds = map(float, cp.get('spectrum', 'thresholds').split(','))
            self.frequencyOffThresholds = map(float, cp.get('spectrum', 'offThresholds').split(','))
            self.frequencyBandOrder = map(int, cp.get('spectrum', 'channelOrder').split(','))

    def _onChunk(self):
        now = datetime.datetime.now()
        if (now - self.lastLightUpdate).total_seconds() > self.delayBetweenUpdates:
            self.lastLightUpdate = now

            spectrum = self.analyzer().spectrum
            bands = [spectrum[i] for i in self.frequencyBandOrder]
            lightStates = [level > self.frequencyThresholds[channel] for channel, level in enumerate(bands)]

            for channel, value in enumerate(lightStates):
                if not value:
                    if self.previousLightStates[channel]:
                        lightStates[channel] = bands[channel] > self.frequencyOffThresholds[channel]

            for channel, value in enumerate(lightStates):
                if self.previousLightStates[channel] != value:
                    GPIO.output(pins[channel], value)

            self.previousLightStates = lightStates

    def onMessage(self, message):
        messageType = message[0]

        if messageType == 'songChange':
            self._onSongChanged(*message[1:])

        elif messageType == 'chunk':
            self._onChunk()


def runLightsProcess(messageQueue, nice=None):
    LightsProcess(messageQueue, nice).loop()


class LightsProcess(QueueHandlerProcess):
    def __init__(self, messageQueue, nice=None):
        super(LightsProcess, self).__init__(nice)

        import spectrum
        self.analyzer = spectrum.SpectrumAnalyzer(self.messageQueue, self.config)

        self.lightController = LightController(self.analyzer, self.config)

    def onMessage(self, messageType, message):
        super(LightsProcess, self).onMessage(messageType, message)

        self.analyzer.onMessage(message)
        self.lightController.onMessage(message)
