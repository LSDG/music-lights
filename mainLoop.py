from __future__ import print_function
import ConfigParser
import collections
import os

import pygame
import pygame.locals

import ansi


currentProcess = None


class QuitApplication(Exception):
    pass


class BaseProcess(object):
    def __init__(self, nice=None):
        global currentProcess
        currentProcess = self

        self.config = ConfigParser.SafeConfigParser()
        self.config.read('config.ini')

        self.queuedCallbacks = collections.deque()

        if nice is not None:
            os.nice(nice)

    def quit(self, event):
        raise QuitApplication

    def eachLoop(self):
        pass

    def afterEachCallback(self):
        pass

    def onShutdown(self):
        pass

    def loop(self):
        ansi.info("Starting process run loop...")

        try:
            while True:
                self.eachLoop()

                # Process any queued callbacks.
                while self.queuedCallbacks:
                    print(self.queuedCallbacks)
                    callback = self.queuedCallbacks.popleft()
                    callback()

                    self.afterEachCallback()

        except QuitApplication:
            print()
            print("Exiting application.")

        except KeyboardInterrupt:
            print()
            print("User interrupted; exiting.")

        finally:
            ansi.info("Process shutting down...")

            self.onShutdown()

            ansi.done()


class QueueHandlerProcess(BaseProcess):
    def __init__(self, messageQueue, nice=None):
        super(QueueHandlerProcess, self).__init__(nice)

        self.messageQueue = messageQueue

    def onMessage(self, messageType, message):
        if messageType == 'end':
            raise QuitApplication()

    def eachLoop(self):
        message = self.messageQueue.get(timeout=60)

        if message:
            messageType = message[0]
            self.onMessage(messageType, message)


class PyGameProcess(BaseProcess):
    def __init__(self, nice=None):
        super(PyGameProcess, self).__init__(nice)

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
        self.processEvent(pygame.event.wait())

    def afterEachCallback(self):
        # Process waiting events before moving on to the next callback.
        for event in pygame.event.get():
            self.processEvent(event)

    def onShutdown(self):
        super(PyGameProcess, self).onShutdown()
        pygame.quit()
