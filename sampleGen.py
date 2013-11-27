import json

import audioread
import hsaudiotag.auto

import ansi

import mainLoop


class SampleGen(object):
    def __init__(self, filenames, config, **kwargs):
        self.framesPerChunk = kwargs.get('framesPerChunk', 1024)

        self.onSongChanged = set()
        self.onStopped = set()
        self.onSample = set()

        self.file = None
        self.totalFramesRead = 0.0
        self.filenameIter = iter(filenames)
        self.currentData = None
        self.sampleIter = None

        self.loadSettings(config)

    def loadSettings(self, gcp):
        self.bytes_per_frame_per_channel = int(gcp.get_def('input', 'bytes_per_frame_per_channel', 2))

    def loadNextFile(self):
        self.currentFilename = next(self.filenameIter).encode('utf-8')

        if self.currentFilename is None:
            mainLoop.currentProcess.queuedCallbacks.append(self.nextChunk)
            return

        print('Loading file {!r}.'.format(self.currentFilename))

        tags = hsaudiotag.auto.File(self.currentFilename)
        if not tags.valid:
            print("Couldn't read tags!")
        else:
            print(json.dumps({
                    'artist': tags.artist,
                    'album': tags.album,
                    'title': tags.title,
                    'duration': tags.duration,
                    }))

        self.tags = tags

        self.file = audioread.audio_open(self.currentFilename)

        songInfo = {
                'channels': self.channels,
                'samplerate': self.samplerate,
                'duration': self.duration
                }
        ansi.info("Loaded song {!r}; channels: {}; samplerate: {}; duration: {} (duration from tags: {})",
                self.currentFilename,
                self.channels,
                self.samplerate,
                self.duration,
                tags.duration
                )

        mainLoop.currentProcess.queueCall(self.onSongChanged, tags, songInfo)

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
        if not self.file:
            return 0

        return self.totalFramesRead / self.file.samplerate

    @property
    def channels(self):
        if not self.file:
            return 0

        return self.file.channels

    @property
    def samplerate(self):
        if not self.file:
            return 0

        return self.file.samplerate

    @property
    def duration(self):
        if not self.file:
            return 0

        return self.file.duration

    def nextChunk(self):
        if self.sampleIter is None:
            self.loadNextFile()

        try:
            data = next(self.sampleIter)
        except (StopIteration, AttributeError):
            # Either we haven't loaded a song yet, or the one we were playing ended. Load another.
            self.loadNextFile()
            data = next(self.sampleIter)

        self.totalFramesRead += self.framesPerChunk

        mainLoop.currentProcess.queueCall(self.onSample, data)

        self.currentData = data
        return data

    def close(self):
        # Stop stream.
        self.file.close()
