from __future__ import print_function
from ConfigParserDefault import ConfigParserDefault
import collections
import functools
import os
from Queue import Empty as QueueEmpty
import traceback

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

        except Exception:
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
        if messageType == 'end':
            raise QuitApplication()

    def eachLoop(self):
        try:
            message = self.messageQueue.get_nowait()

            messageType = message[0]
            self.onMessage(messageType, message)
        except QueueEmpty:
            pass
