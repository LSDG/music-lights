from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys
import json

import player

from gevent import monkey, Greenlet; monkey.patch_all()

from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin


class WebController(object):
    def __init__(self, siteUrl, server):
        self.server = server
        self.playerQueue = Queue()
        self.controllerQueue = Queue()
        self.playerProcess = Process(target=player.Run, args=(self.playerQueue, self.controllerQueue))

        self.playerQueueLet = Greenlet.spawn(self.processPlayerQueue)

    def processPlayerQueue(self):
        while True:
            msg = self.playerQueue.get()

            self.broadcast_event(msg)
            print msg

    def relayMessage(self, msg):
        self.playerQueue.put(msg)

        if msg['command'] == 'stop':
            print 'Got stop command!'
        elif msg['command'] == 'playnext':
            print 'Playing next:', msg['filename']

    def broadcast_event(self, event, *args):
        """
        This is sent to all in the sockets in this particular Namespace,
        including itself.
        """
        pkt = dict(type="event",
                   name=event,
                   args=args,
                   endpoint='')

        for sessid, socket in self.server.sockets.iteritems():
            socket.send_packet(pkt)



class ControllerNamespace(BaseNamespace, BroadcastMixin):
    def recv_message(self, data):
        controller.relayMessage(data)


class Application(object):
    def __init__(self):
        pass

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO'].strip('/')

        if path.startswith('socket.io'):
            socketio_manage(environ, {'': ControllerNamespace}, self.request)


if __name__ == '__main__':
    server = SocketIOServer(('0.0.0.0', 8080), Application(), resource='socket.io')

    controller = WebController('localhost', server)

    server.serve_forever()


