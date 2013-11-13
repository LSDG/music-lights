from __future__ import print_function
from ConfigParserDefault import ConfigParserDefault
import collections
import functools
import os
from Queue import Empty as QueueEmpty
import traceback

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

        self.config = ConfigParserDefault()
        self.config.read('config.ini')

        self.queuedCallbacks = collections.deque()

        if nice is not None:
            os.nice(nice)

    def quit(self, event=None):
        raise QuitApplication

    def eachLoop(self):
        pass

    def afterEachCallback(self):
        pass

    def onShutdown(self):
        pass

    def queueCall(self, funcOrSet, *args, **kwargs):
        if not funcOrSet:
            return

        if isinstance(funcOrSet, set):
            func = functools.partial(self.callCallbacks, funcOrSet, *args, **kwargs)
        else:
            func = functools.partial(self.callCallbacks, [funcOrSet], *args, **kwargs)

        self.queuedCallbacks.append(func)

    def callCallbacks(self, callbacks, *args, **kwargs):
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except:
                print("Exception calling {!r}(*{!r}, **{!r}):".format(cb, args, kwargs), traceback.format_exc())

    def loop(self):
        ansi.info("Starting process run loop...")

        try:
            while True:
                self.eachLoop()

                # Process any queued callbacks.
                while self.queuedCallbacks:
                    callback = self.queuedCallbacks.popleft()
                    callback()

                    self.afterEachCallback()

        except QuitApplication:
            print()
            print("Exiting application.")

        except KeyboardInterrupt:
            print()
            print("User interrupted; exiting.")

        except Exception as ex:
            print('Got Exception while looping:', traceback.format_exc())

        finally:
            ansi.info("Process shutting down...")

            self.onShutdown()

            ansi.done()


class QueueHandlerProcess(BaseProcess):
    def __init__(self, messageQueue, nice=None):
        super(QueueHandlerProcess, self).__init__(nice)

        self.messageQueue = messageQueue

    def onMessage(self, messageType, message):
        # print('QueueHandler onMessage')
        if messageType == 'end':
            raise QuitApplication()

    def eachLoop(self):
        # print('QueueHandler eachLoop')
        try:
            message = self.messageQueue.get_nowait()
            # print('QueueHandler after get_nowait')

            messageType = message[0]
            # print('About to call onMessage')
            self.onMessage(messageType, message)
        except QueueEmpty:
            # print('QueueEmpty')
            pass
        #except Exception as exc:
        #    print('Exception while reading from queue:', exc)


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
        # print('PyGame eachLoop')
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
