import alsaaudio

import ansi

import mainLoop


class SampleOutput(object):
    def __init__(self, sampleGen, config):
        self.sampleGen = sampleGen
        sampleGen.onSongChanged.add(self.onSongChanged)

        self.pcm = None

        self.debug = config.get_def('output', 'debug', 'f').lower() not in ('f', 'false', 'n', 'no', '0', 'off')

    def onSongChanged(self, *args, **kwargs):
        ansi.debug('onSongChanged')

        if self.pcm:
            self.pcm.close()

        self.pcm = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK)  # mode=alsaaudio.PCM_NORMAL)

        if self.debug:
            ansi.debug('Song changed; channels: {}; samplerate: {}; period size: {}',
                    self.sampleGen.channels, self.sampleGen.samplerate, self.sampleGen.framesPerChunk)

        self.pcm.setchannels(self.sampleGen.channels)
        self.pcm.setrate(self.sampleGen.samplerate)
        self.pcm.setperiodsize(self.sampleGen.framesPerChunk)
        self.pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)

    def play(self):
        mainLoop.currentProcess.afterEachLoop = self.queueNextSound

    def queueNextSound(self, event=None):
        if self.debug:
            ansi.stdout(
                    "{cursor.col.0}{clear.line.all}Current time:"
                        " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                    file=self.sampleGen,
                    suppressNewline=True
                    )

        chunk = self.sampleGen.nextChunk()
        if self.pcm:
            self.pcm.write(chunk)


class ALSAProcess(mainLoop.QueueHandlerProcess):
    def __init__(self, messageQueue, nice=None):
        super(ALSAProcess, self).__init__(messageQueue, nice)

        self.afterEachLoop = None

    def eachLoop(self):
        super(ALSAProcess, self).eachLoop()

        if self.afterEachLoop:
            self.afterEachLoop()
