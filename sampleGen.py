import audioread

import mainLoop


class SampleGen(object):
    def __init__(self, filenames, config, **kwargs):
        self.framesPerChunk = kwargs.get('framesPerChunk', 4096)

        self.onSongChanged = set()
        self.onStopped = set()
        self.onSample = set()

        self.totalFramesRead = 0.0
        self.filenameIter = iter(filenames)
        self.currentData = None
        self.sampleIter = None

        self.loadSettings(config)

    def loadSettings(self, gcp):
        self.bytes_per_frame_per_channel = int(gcp.get('main', 'bytes_per_frame_per_channel', 2))

    def _loadNextFile(self):
        self.currentFilename = next(self.filenameIter)
        print('Loading file {!r}.'.format(self.currentFilename))

        mainLoop.currentProcess.queuedCallbacks.extend(self.onSongChanged)

        self.file = audioread.audio_open(self.currentFilename)

        blockSize = self.framesPerChunk * self.file.channels * self.bytes_per_frame_per_channel
        try:
            # MAD (pymad)
            self.sampleIter = self.file.read_blocks(blockSize)
        except AttributeError:
            try:
                # FFMpeg (command line)
                self.sampleIter = self.file.read_data(blockSize)
            except AttributeError:
                # gstreamer (pygst)
                self.sampleIter = iter(self.file)

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

        try:
            self.currentData = next(self.sampleIter)
        except (StopIteration, AttributeError):
            # Either we haven't loaded a song yet, or the one we were playing ended. Load another.
            self._loadNextFile()
            self.currentData = next(self.sampleIter)

        self.totalFramesRead += self.framesPerChunk

        mainLoop.currentProcess.queuedCallbacks.extend(self.onSample)

        return self.currentData

    def nextChunkSound(self):
        import pygame
        return pygame.mixer.Sound(buffer(self.nextChunk()))

    def close(self):
        # Stop stream.
        self.file.close()
