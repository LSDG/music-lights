try:
    import sfml
    sfmlVer = 2
except ImportError:
    from PySFML import sf as sfml
    sfmlVer = 1

import ansi

import mainLoop


class BaseSFMLSampleOutput(sfml.SoundStream):
    def __init__(self, sampleGen):
        ansi.debug('__init__')
        sfml.SoundStream.__init__(self)

        self.sampleGen = sampleGen
        sampleGen.onSongChanged.add(self.onSongChanged)

    def onSongChanged(self, *args, **kwargs):
        ansi.debug('onSongChanged')
        if (self.channel_count, self.sample_rate) != (self.sampleGen.channels, self.sampleGen.samplerate):
            self.initialize(self.sampleGen.channels, self.sampleGen.samplerate)

    def getData(self):
        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=self.sampleGen,
                suppressNewline=True
                )

        # fill the chunk with audio data from the stream source
        return self.sampleGen.nextChunk()

    def play(self):
        ansi.debug('play')
        self.sampleGen.loadNextFile()
        mainLoop.currentProcess.queueCall(self._finishPlay)

    def on_get_data(self, data):
        ansi.debug('on_get_data')
        # fill the chunk with audio data from the stream source
        data += self.getData()

        # return true to continue playing
        return True


if sfmlVer == 2:
    class SampleOutput(BaseSFMLSampleOutput):
        def _finishPlay(self):
            ansi.debug('_finishPlay (sfml2)')
            sfml.SoundStream.play(self)

else:
    class SampleOutput(BaseSFMLSampleOutput):
        def _finishPlay(self):
            ansi.debug('_finishPlay')
            self.Play()

        def initialize(self, *args, **kwargs):
            ansi.debug('initialize')
            self.Initialize(*args, **kwargs)

        def OnGetData(self):
            ansi.debug('OnGetData')
            return self.getData()

        @property
        def channel_count(self):
            ansi.debug('channel_count')
            return self.GetChannelsCount()

        @property
        def sample_rate(self):
            ansi.debug('sample_rate')
            return self.GetSampleRate()
