from __future__ import print_function
import datetime
import time
from weakref import ref

import serial

import ansi

from ConfigParserDefault import ConfigParserDefault
from mainLoop import QueueHandlerProcess
from songConfig import SongConfig


gcp = ConfigParserDefault()
gcp.read('config.ini')

serialDevice = gcp.get_def('serial', 'device', '/dev/ttyAMA0')
serialSpeed = int(gcp.get_def('serial', 'speed', 115200))
serialDebug = gcp.get_def('serial', 'debug', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')

delayBetweenUpdates = float(gcp.get_def('lights', 'delayBetweenUpdates', 0.05))


class LightController(object):
    def __init__(self, analyzer, config):
        self.analyzer = ref(analyzer)

        self.songConfig = SongConfig(config)

        ansi.info('Serial connecting to {} at {} bps', serialDevice, serialSpeed)
        self.serial = serial.Serial(serialDevice, serialSpeed, timeout=1)

        # Assume we're already started unless we're using the USB interface to the Arduino.
        self.ready = 'ttyACM' not in serialDevice
        while not self.ready:
            if self.readFromSerial().startswith('LSDG Holiday Light controller ver '):
                self.ready = True

        self.lastLightUpdate = datetime.datetime.now()
        self.previousLightStates = [False] * analyzer.frequencyBands
        self.lightUpdateTimes = [time.time() for x in range(int(config.get('spectrum', 'frequencyBands')))]

    def readFromSerial(self):
        data = self.serial.readline()
        if serialDebug:
            ansi.stdout(
                    "{style.bold.fg.black} Arduino -> RPi:{style.none} {data!r}",
                    data=data
                    )
        return data

    def writeToSerial(self, data):
        if serialDebug:
            ansi.stdout(
                    "{style.bold.fg.black}Arduino <- RPi :{style.none} {data!r}",
                    data=data
                    )
        self.serial.write(data)

    def _onChunk(self):
        spectrum = self.analyzer().spectrum

        if spectrum is not None:
            spectrumBands = len(spectrum) - 1
            bands = [spectrum[min(i, spectrumBands)] for i in self.songConfig.frequencyBandOrder]
            lightStates = [level > self.songConfig.frequencyThresholds[channel] for channel, level in enumerate(bands)]

            changeCmd = []
            for channel, value in enumerate(lightStates):
                if self.previousLightStates[channel] != value  and (time.time() - self.lightUpdateTimes[channel] > 0.2):
                    self.lightUpdateTimes[channel] = time.time()
                    changeCmd.append('p{}s{}'.format(channel, 1 if value else 0))

            if changeCmd:
                self.writeToSerial(''.join(changeCmd) + '\n')

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
        super(LightsProcess, self).__init__(messageQueue, nice)

        import spectrum
        self.analyzer = spectrum.SpectrumAnalyzer(self.messageQueue, self.config)

        self.lightController = LightController(self.analyzer, self.config)

    def onMessage(self, messageType, message):
        super(LightsProcess, self).onMessage(messageType, message)

        self.analyzer.onMessage(message)
        self.lightController.onMessage(message)


class LightsTestProcess(LightsProcess):
    def __init__(self, messageQueue, nice=None):
        super(LightsTestProcess, self).__init__(messageQueue, nice)

        import itertools
        self.testCommands = iter(itertools.cycle((
            'p4s0p1s0p2s0p3s0',
            'p4s1p1s1p2s1p3s1',
            'p4s0p1s1p2s0p3s1',
            'p4s1p1s0p2s1p3s0',
            )))

    def eachLoop(self):
        super(LightsTestProcess, self).eachLoop()

        time.sleep(0.2)
        nextCommand = next(self.testCommands)
        self.lightController.writeToSerial(nextCommand + '\n')


if __name__ == '__main__':
    print("Starting lights.py as main app...")

    from multiprocessing import Queue

    #runLightsProcess(Queue())

    lp = LightsTestProcess(Queue())
    lp.loop()
