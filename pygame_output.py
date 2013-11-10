import pygame.mixer
import pygame.locals

import ansi

import mainLoop


DONE_PLAYING_CHUNK = pygame.locals.USEREVENT


class SampleOutput(object):
    def __init__(self, sampleGen):
        self.sampleGen = sampleGen

        self.channel = pygame.mixer.Channel(0)

        self.channel.set_endevent(DONE_PLAYING_CHUNK)
        mainLoop.currentProcess.eventHandlers[DONE_PLAYING_CHUNK] = self.queueNextSound

    def play(self):
        self.queueNextSound()  # Start playing the first chunk.
        self.queueNextSound()  # Queue the next chunk.

    def queueNextSound(self, event=None):
        ansi.stdout(
                "{cursor.col.0}{clear.line.all}Current time:"
                    " {style.bold}{file.elapsedTime: >7.2f}{style.none} / {file.duration: <7.2f}",
                file=self.sampleGen,
                suppressNewline=True
                )

        chunk = pygame.mixer.Sound(buffer(self.sampleGen.nextChunk()))

        chunk.play()
