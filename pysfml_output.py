import sfml

import ansi


class SampleOutput(sfml.SoundStream):
    def __init__(self, sampleGen):
        sfml.SoundStream.__init__(self)

        self.sampleGen = sampleGen
        sampleGen.onSongChanged.add(self.onSongChanged)

    def play(self):
        self.sampleGen.loadNextFile()
        sfml.SoundStream.play(self)

    def onSongChanged(self, *args, **kwargs):
        if (self.channel_count, self.sample_rate) != (self.sampleGen.channels, self.sampleGen.samplerate):
            self.initialize(self.sampleGen.channels, self.sampleGen.samplerate)

    def on_get_data(self, data):
        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=self.sampleGen,
                suppressNewline=True
                )

        # fill the chunk with audio data from the stream source
        data += self.sampleGen.nextChunk()

        # return true to continue playing
        return True
