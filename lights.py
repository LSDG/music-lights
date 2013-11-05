from __future__ import print_function
import datetime
from weakref import ref

import serial

from mainLoop import QueueHandlerProcess
from songConfig import SongConfig


class LightController(object):
    def __init__(self, analyzer, config):
        self.analyzer = ref(analyzer)
        self.lastLightUpdate = datetime.datetime.now()

        self.songConfig = SongConfig(config)

        #TODO: Read serial port from config
        self.serial = serial.Serial('/dev/ttyUSB0', 19200, timeout=1)

        self.previousLightStates = [False] * analyzer.frequencyBands

    def _onChunk(self):
        now = datetime.datetime.now()
        if (now - self.lastLightUpdate).total_seconds() > self.delayBetweenUpdates:
            self.lastLightUpdate = now

            spectrum = self.analyzer().spectrum
            bands = [spectrum[i] for i in self.songConfig.frequencyBandOrder]
            lightStates = [level > self.songConfig.frequencyThresholds[channel] for channel, level in enumerate(bands)]

            for channel, value in enumerate(lightStates):
                if not value:
                    if self.previousLightStates[channel]:
                        lightStates[channel] = bands[channel] > self.songConfig.frequencyOffThresholds[channel]

            changeCmd = []
            for channel, value in enumerate(lightStates):
                if self.previousLightStates[channel] != value:
                    changeCmd.append('p{}s{}'.format(channel, 1 if value else 0))

            self.serial.write(''.join(changeCmd) + '\n')

            self.previousLightStates = lightStates

    def onMessage(self, message):
        messageType = message[0]

        if messageType == 'songChange':
            self.songConfig.loadSongSettings(*message[1:])

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
