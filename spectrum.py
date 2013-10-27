from __future__ import print_function

from numpy import array_split, short, fromstring
from numpy.random import rand as rand_array

import anfft


# Warm up ANFFT, allowing it to determine which FFT algorithm will work fastest on this machine.
anfft.fft(rand_array(1024), measure=True)


class SpectrumAnalyzer(object):
    def __init__(self, messageQueue, config):
        self.messageQueue = messageQueue
        self._dataSinceLastSpectrum = []

        self.loadSettings(config)

    def loadSettings(self, gcp):
        # The number of spectrum analyzer bands (also light output channels) to use.
        self.frequencyBands = int(gcp.get_def('main', 'frequencyBands', 16))

        self.bytes_per_frame_per_channel = int(gcp.get_def('main', 'bytes_per_frame_per_channel', 2))

    def _onChunk(self, data):
        self._currentSpectrum = None
        self._dataSinceLastSpectrum.append(data)

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

    def onMessage(self, message):
        messageType = message[0]

        if messageType == 'chunk':
            self._onChunk(*message[1:])
