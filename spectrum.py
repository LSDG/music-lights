from __future__ import print_function
import math

from numpy import short, fromstring
from numpy.fft import fftfreq

import pyfftw

import ansi

import mainLoop


alpha = 0.53836
beta = 0.46164


def chunks(sequence, chunkCount):
    itemCount = len(sequence)
    chunkSize = itemCount / chunkCount
    for chunkNum in range(0, chunkCount):
        start = chunkNum * chunkSize
        yield sequence[int(round(start)):int(round(start + chunkSize))]


def avg(sequence):
    return sum(sequence) / len(sequence)


class SpectrumAnalyzer(object):
    def __init__(self, messageQueue, config, keepZeroBand=False):
        self.messageQueue = messageQueue

        self.onSpectrum = set()

        self._currentSpectrum = None
        self._dataSinceLastSpectrum = []
        self._samplerate = 1
        self.channels = 2
        self.keepZeroBand = keepZeroBand

        self.loadSettings(config)

        # Warm up pyFFTW, allowing it to determine which FFT algorithm will work fastest on this machine.
        buf = pyfftw.n_byte_align_empty(self.framesPerWindow, pyfftw.simd_alignment, 'float64')
        self.fft = pyfftw.builders.rfft(buf, threads=self.fftThreads, overwrite_input=True)  # , avoid_copy=True)

        self.dataBuffer = self.fft.get_input_array()

    def loadSettings(self, gcp):
        # The number of spectrum analyzer bands (also light output channels) to use.
        self.frequencyBands = int(gcp.get_def('spectrum', 'frequencyBands', 16))

        # From http://docs.scipy.org/doc/numpy/reference/routines.fft.html#real-and-hermitian-transforms:
        # > The family of rfft functions is designed to operate on real inputs, and exploits this symmetry by
        # > computing only the positive frequency components, up to and including the Nyquist frequency. Thus, n
        # > input points produce n/2+1 complex output points.
        #
        # Since we want `frequencyBands` channels, not including negative frequencies or the zero frequency, we
        # actually want to generate `frequencyBands + 1` bands according to the above definition.
        # Solving `b+1 = n/2+1` for `n` gives us `n = 2b`, so we generate each slice of the spectrum using
        # `2 * frequencyBands` frames.
        self.framesPerSlice = 2 * self.frequencyBands

        # Average `sliceWindow` slices to get the spectrum for each call to onSpectrum.
        self.sliceWindow = int(gcp.get_def('spectrum', 'sliceWindow', 16))

        self.framesPerWindow = self.framesPerSlice * self.sliceWindow

        self.windowCoefficients = self.hamming()

        self.bytes_per_frame_per_channel = int(gcp.get_def('input', 'bytes_per_frame_per_channel', 2))

        self.fftThreads = int(gcp.get_def('spectrum', 'fftThreads', 1))

        # Pre-calculate the constant used to normalize the signal data.
        self.normalizationConst = float(2 ** (self.bytes_per_frame_per_channel * 8))

        self.debug = gcp.get_def('spectrum', 'debug', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')

    def hamming(self):
        """Simple implementation of a Hamming window function.

        See https://en.wikipedia.org/wiki/Window_function#Hamming_window

        """
        innerCoefficient = 2 * math.pi / (self.framesPerWindow - 1)

        return [alpha - beta * math.cos(innerCoefficient * frameNum)
                for frameNum in range(self.framesPerWindow)]

    @property
    def bytesPerFrame(self):
        return self.bytes_per_frame_per_channel * self.channels

    def _onChunk(self, data):
        self._currentSpectrum = None
        self._dataSinceLastSpectrum.append(data)

    def calcWindow(self, channelData, windowNum):
        fromFrame = windowNum * self.framesPerWindow
        toFrame = fromFrame + self.framesPerWindow

        fftOut = []
        outputsPerChannel = int(self.frequencyBands / float(self.channels))
        for channel in channelData:
            self.dataBuffer[:] = self.windowCoefficients * channel[fromFrame:toFrame] / self.normalizationConst

            channelFFTOut = self.fft()

            fftOut.extend(map(
                    avg,
                    chunks(
                        abs(channelFFTOut[0 if self.keepZeroBand else 1:len(channelFFTOut) / 2 + 1]),
                        outputsPerChannel
                        )
                    ))

        return fftOut

    @property
    def spectrum(self):
        if self._currentSpectrum is None:
            rawData = ''.join(self._dataSinceLastSpectrum)

            numWindows = int(math.floor(len(rawData) / self.bytesPerFrame / self.framesPerWindow))
            if numWindows == 0:
                if self.debug:
                    ansi.warn("Need {} frames for a window! (only have {})",
                            self.framesPerWindow, len(rawData) / self.bytesPerFrame)
                return

            if len(rawData) % (self.framesPerWindow * self.bytesPerFrame) != 0:
                self._dataSinceLastSpectrum = [rawData[numWindows * self.framesPerWindow * self.bytesPerFrame:]]
                rawData = rawData[:numWindows * self.framesPerWindow * self.bytesPerFrame]
            else:
                self._dataSinceLastSpectrum = []

            dataArr = fromstring(rawData, dtype=short)

            # Reshape the array so we can chop it to the correct number of frames.
            dataArr = dataArr.reshape((-1, self.channels))

            if not self.onSpectrum:
                # No per-spectrum listeners, so ditch all but the most recent spectrum window.
                dataArr = dataArr[-self.framesPerWindow:]
                numWindows = 1

            for windowNum in range(numWindows):
                fftOut = self.calcWindow(dataArr.T, windowNum)

                mainLoop.currentProcess.queueCall(self.onSpectrum, fftOut)

            self._currentSpectrum = fftOut

        return self._currentSpectrum

    def fftFrequencies(self, sampleRate):
        frequencies = fftfreq(self.framesPerSlice) * sampleRate
        startFreq = 0 if self.keepZeroBand else 1
        ansi.info("Total generated frequency bands: {} {!r}", len(frequencies), frequencies)
        ansi.info("Trimmed frequency bands: {} {!r}",
                len(frequencies[startFreq:self.frequencyBands + 1]),
                abs(frequencies[startFreq:self.frequencyBands + 1])
                )

        # From http://docs.scipy.org/doc/numpy/reference/routines.fft.html#implementation-details:
        # > For an even number of input points, A[n/2] represents both positive and negative Nyquist frequency, and is
        # > also purely real for real input.
        #
        # Since numpy gives us -0.5 as the frequency of A[n/2], we need to call abs() on the frequencies for it to make
        # sense.
        return abs(frequencies[startFreq:self.frequencyBands + 1])

    def onMessage(self, message):
        messageType = message[0]

        if messageType == 'songChange':
            filename, fileInfo = message[1:3]
            self._samplerate = fileInfo['samplerate']
            self.channels = fileInfo['channels']

            # Recalculate window coefficients, in case the number of channels changed.
            self.windowCoefficients = self.hamming()

        elif messageType == 'chunk':
            self._onChunk(*message[1:])
