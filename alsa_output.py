import alsaaudio

import ansi

import mainLoop


class SampleOutput(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen
        sampleGen.onSongChanged.add(self.onSongChanged)

        card = alsaaudio.cards()[0]
        self.pcm = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK, mode=alsaaudio.PCM_NORMAL, card=card)

    def onSongChanged(self, *args, **kwargs):
        ansi.debug('onSongChanged')

        self.pcm.setchannels(self.sampleGen.channels)
        self.pcm.setrate(self.sampleGen.samplerate)
        self.pcm.setperiodsize(self.sampleGen.framesPerChunk)

    def play(self):
        mainLoop.currentProcess.afterEachLoop = self.queueNextSound

    def queueNextSound(self, event=None):
        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=self.sampleGen,
                suppressNewline=True
                )

        self.pcm.write(self.sampleGen.nextChunk())


class ALSAProcess(mainLoop.QueueHandlerProcess):
    def __init__(self, messageQueue, nice=None):
        super(ALSAProcess, self).__init__(messageQueue, nice)

        self.afterEachLoop = None

    def eachLoop(self):
        super(ALSAProcess, self).eachLoop()

        if self.afterEachLoop:
            self.afterEachLoop()
