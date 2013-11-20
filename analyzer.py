import csv
from multiprocessing import Queue
from Queue import Full as QueueFull
import sys

import ansi

import mainLoop
from sampleGen import SampleGen
from spectrum import SpectrumAnalyzer


class AnalyzerProcess(mainLoop.QueueHandlerProcess):
    def __init__(self, csvFilename, *playlist):
        super(AnalyzerProcess, self).__init__(Queue())

        self.playlist = playlist

        self.sampleGen = SampleGen(playlist, self.config)
        self.sampleGen.onSample.add(self._onSample)
        self.sampleGen.onSongChanged.add(self._onSongChanged)

        self.analyzer = SpectrumAnalyzer(self.messageQueue, self.config, keepZeroBand=True)

        self.csvFile = open(csvFilename, 'wb')
        self.csv = csv.writer(self.csvFile)

    def _onSongChanged(self, tags, songInfo):
        print()
        ansi.stdout(
                "Analyzing audio file: {style.fg.blue}{file.currentFilename}{style.none}\n"
                    "{style.bold.fg.black}channels:{style.none} {file.channels}"
                    "   {style.bold.fg.black}sample rate:{style.none} {file.samplerate} Hz"
                    "   {style.bold.fg.black}duration:{style.none} {file.duration} s",
                file=self.sampleGen
                )

        try:
            self.messageQueue.put_nowait(('songChange', self.sampleGen.currentFilename, songInfo))
        except QueueFull:
            ansi.error("Message queue to light process full! Continuing...")

        self.csv.writerow([
            '{} Hz'.format(f)
            for f in self.analyzer.fftFrequencies(self.sampleGen.samplerate)
            ])

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
            self.csv.writerow(spectrum)

    def onShutdown(self):
        super(AnalyzerProcess, self).onShutdown()
        self.csvFile.close()


if __name__ == '__main__':
    AnalyzerProcess(*sys.argv[1:]).loop()
