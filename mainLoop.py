from __future__ import print_function
from ConfigParserDefault import ConfigParserDefault
import collections
import os
from Queue import Empty as QueueEmpty

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

        func = funcOrSet
        if isinstance(funcOrSet, set):
            func = lambda: [f(*args, **kwargs) for f in funcOrSet]

        self.queuedCallbacks.append(func)

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
        try:
            message = self.messageQueue.get_nowait()

            messageType = message[0]
            self.onMessage(messageType, message)
        except QueueEmpty:
            pass
        #except Exception as exc:
        #    print('Exception while reading from queue:', exc)
