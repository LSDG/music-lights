import csv
from multiprocessing import Queue
from Queue import Full as QueueFull
import sys

import ansi

from mainLoop import QueueHandlerProcess
from sampleGen import SampleGen
from songConfig import SongConfig
from spectrum import SpectrumAnalyzer


class AnalyzerProcess(QueueHandlerProcess):
    def __init__(self, csvFilename, *playlist):
        super(AnalyzerProcess, self).__init__(Queue())

        self.playlist = playlist

        self.songConfig = SongConfig(self.config)

        self.sampleGen = SampleGen(playlist, self.config)
        self.sampleGen.onSample.add(self._onSample)
        self.sampleGen.onSongChanged.add(self._onSongChanged)

        self.analyzer = SpectrumAnalyzer(self.messageQueue, self.config)

        self.csvFile = open(csvFilename, 'wb')
        self.csv = csv.writer(self.csvFile)

    def _onSongChanged(self, tags):
        print()
        ansi.stdout(
                "Playing audio file: {style.fg.blue}{file.currentFilename}{style.none}\n"
                    "{style.bold.fg.black}channels:{style.none} {file.channels}"
                    "   {style.bold.fg.black}sample rate:{style.none} {file.samplerate} Hz"
                    "   {style.bold.fg.black}duration:{style.none} {file.duration} s",
                file=self.sampleGen
                )

        self.songConfig.loadSongSettings(self.sampleGen.currentFilename)

        try:
            self.messageQueue.put_nowait(('songChange', self.sampleGen.currentFilename))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def _onSample(self, data):
        try:
            self.messageQueue.put_nowait(('chunk', data))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

    def eachLoop(self):
        super(AnalyzerProcess, self).eachLoop()

        try:
            self.sampleGen.nextChunk()
        except StopIteration:
            self.quit()

    def onMessage(self, messageType, message):
        super(AnalyzerProcess, self).onMessage(messageType, message)

        self.analyzer.onMessage(message)

        if messageType == 'chunk':
            spectrum = self.analyzer.spectrum
            bands = [spectrum[i] for i in self.songConfig.frequencyBandOrder]
            self.csv.writerow(bands)

    def onShutdown(self):
        super(AnalyzerProcess, self).onShutdown()
        self.csvFile.close()


if __name__ == '__main__':
    AnalyzerProcess(*sys.argv[1:]).loop()
