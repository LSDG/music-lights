from __future__ import print_function
import math

from numpy import short, fromstring
from numpy.fft import fftfreq

import pyfftw

import mainLoop


class SpectrumAnalyzer(object):
    def __init__(self, messageQueue, config):
        self.messageQueue = messageQueue

        self.onSpectrum = set()

        self._currentSpectrum = None
        self._dataSinceLastSpectrum = []
        self._samplerate = 1

        self.loadSettings(config)

        # Warm up pyFFTW, allowing it to determine which FFT algorithm will work fastest on this machine.
        buf = pyfftw.n_byte_align_empty(self.samplesPerSlice, pyfftw.simd_alignment, 'float64')
        self.fft = pyfftw.builders.rfft(buf, threads=self.fftThreads, overwrite_input=True)#, avoid_copy=True)

        self.dataBuffer = self.fft.get_input_array()

    def loadSettings(self, gcp):
        # The number of spectrum analyzer bands (also light output channels) to use.
        self.frequencyBands = int(gcp.get_def('main', 'frequencyBands', 16))

        # From http://docs.scipy.org/doc/numpy/reference/routines.fft.html#real-and-hermitian-transforms:
        # > The family of rfft functions is designed to operate on real inputs, and exploits this symmetry by
        # > computing only the positive frequency components, up to and including the Nyquist frequency. Thus, n
        # > input points produce n/2+1 complex output points.
        #
        # Since we want `frequencyBands` channels, not including negative frequencies or the zero frequency, we
        # actually want to generate `frequencyBands + 1` bands according to the above definition.
        # Solving `b+1 = n/2+1` for `n` gives us `n = 2b`, so we generate each slice of the spectrum using
        # `2 * frequencyBands` samples.
        self.samplesPerSlice = 2 * self.frequencyBands

        # Average `sliceWindow` samples to get the spectrum for each call to onSpectrum.
        self.sliceWindow = int(gcp.get_def('main', 'sliceWindow', 16))

        self.samplesPerWindow = self.samplesPerSlice * self.sliceWindow

        self.bytes_per_frame_per_channel = int(gcp.get_def('main', 'bytes_per_frame_per_channel', 2))

        self.fftThreads = int(gcp.get_def('main', 'fftThreads', 1))

        # Pre-calculate the constant used to normalize the signal data.
        self.normalizationConst = float(2 ** (self.bytes_per_frame_per_channel * 8))

    def _onChunk(self, data):
        self._currentSpectrum = None
        self._dataSinceLastSpectrum.append(data)

    def calcSlice(self, dataArr, sliceNum):
        fromSample = sliceNum * self.samplesPerSlice
        toSample = fromSample + self.samplesPerSlice

        self.dataBuffer[:] = dataArr[fromSample:toSample] / self.normalizationConst

        fftOut = self.fft()

        # Cut the spectrum down to the appropriate number of bands. (ditch the zero-frequency band and the negative
        # frequencies)
        return abs(fftOut[1:self.frequencyBands + 1])

    def calcWindow(self, dataArr, windowNum):
        return map(
                (lambda arr: sum(arr) / self.sliceWindow),
                zip(*[
                    self.calcSlice(dataArr, windowNum * self.sliceWindow + sliceNum)
                    for sliceNum in range(self.sliceWindow)
                    ])
                )

    @property
    def spectrum(self):
        if self._currentSpectrum is None:
            rawData = ''.join(self._dataSinceLastSpectrum)

            numWindows = int(math.floor(len(rawData) / self.bytes_per_frame_per_channel / self.samplesPerWindow))
            if numWindows == 0:
                print("Need {} samples for a window! (only have {})"
                        .format(self.samplesPerWindow, len(rawData) / self.bytes_per_frame_per_channel))
                print(self._dataSinceLastSpectrum)
                return [0 for _ in range(self.frequencyBands)]

            if len(rawData) % (self.samplesPerWindow * self.bytes_per_frame_per_channel) != 0:
                self._dataSinceLastSpectrum = [rawData[numWindows * self.samplesPerWindow:]]
                rawData = rawData[:numWindows * self.samplesPerWindow]
            else:
                self._dataSinceLastSpectrum = []

            dataArr = fromstring(rawData, dtype=short)

            if not self.onSpectrum:
                # No per-spectrum listeners, so ditch all but the most recent spectrum window.
                dataArr = dataArr[-self.samplesPerWindow:]
                numWindows = 1

            for windowNum in range(numWindows):
                fftOut = self.calcWindow(dataArr, windowNum)

                mainLoop.currentProcess.queueCall(self.onSpectrum, fftOut)

            self._currentSpectrum = fftOut

        return self._currentSpectrum

    @property
    def fftFrequencies(self):
        frequencies = fftfreq(self.samplesPerSlice)
        print("Total generated frequency bands: {} {!r}".format(
                len(frequencies),
                frequencies
                ))
        print("Trimmed frequency bands: {} {!r}".format(
                len(frequencies[1:self.frequencyBands + 1]),
                abs(frequencies[1:self.frequencyBands + 1])
                ))

        # From http://docs.scipy.org/doc/numpy/reference/routines.fft.html#implementation-details:
        # > For an even number of input points, A[n/2] represents both positive and negative Nyquist frequency, and is
        # > also purely real for real input.
        #
        # Since numpy gives us -0.5 as the frequency of A[n/2], we need to call abs() on the frequencies for it to make
        # sense.
        return abs(frequencies[1:self.frequencyBands + 1]) * self._samplerate

    def onMessage(self, message):
        messageType = message[0]

        if messageType == 'songChange':
            filename, fileInfo = message[1:3]
            self._samplerate = fileInfo['samplerate']

        elif messageType == 'chunk':
            self._onChunk(*message[1:])
