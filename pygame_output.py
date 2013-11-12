import pygame
import pygame.event
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


class PyGameProcess(QueueHandlerProcess):
    def __init__(self, messageQueue, nice=None):
        super(PyGameProcess, self).__init__(messageQueue, nice)

        self.eventHandlers = {
                pygame.locals.QUIT: self.quit,
                }

        pygame.init()

    def unhandledEvent(self, event):
        ansi.warn("Unhandled event! {!r}", event)

    def processEvent(self, event):
        if event.type == pygame.locals.NOEVENT:
            return

        handler = self.eventHandlers.get(event.type, self.unhandledEvent)
        handler(event)

    def eachLoop(self):
        super(PyGameProcess, self).eachLoop()

        #self.processEvent(pygame.event.wait())
        self.afterEachCallback()

    def afterEachCallback(self):
        # Process waiting events before moving on to the next callback.
        for event in pygame.event.get():
            self.processEvent(event)

    def onShutdown(self):
        super(PyGameProcess, self).onShutdown()
        pygame.quit()
