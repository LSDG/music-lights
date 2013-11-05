from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys
import hsaudiotag.auto
import json

import player

from gevent import monkey, Greenlet; monkey.patch_all()

from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

files = sys.argv[1:]

class WebController(object):
    def __init__(self, server):
        self.server = server
        self.playerQueue = Queue()
        self.controllerQueue = Queue()
        self.playlist = self.generatePlaylist()
        self.playerProcess = Process(target=player.runPlayerProcess, args=(self.playerQueue, self.controllerQueue))

        self.playerQueueLet = Greenlet.spawn(self.processPlayerQueue)

    def processPlayerQueue(self):
        while True:
            msg = self.playerQueue.get()

            self.broadcast_event(msg)
            print msg

    def handleMessage(self, msg):
        self.playerQueue.put(msg)

        if msg['command'] == 'stop':
            print 'Got stop command!'
        elif msg['command'] == 'play next':
            print 'Playing next:', msg['filename']
        elif msg['command'] == 'list songs':
            self.broadcast_event()

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

    def generatePlaylist(self):
        playlist = list()
        for file in files:
            tags = hsaudiotag.auto.File(file)
            if not tags.valid:
                entry = json.dumps({
                    'title': file,
                    'filename': file
                })
            else:
                entry = json.dumps({
                    'artist': tags.artist,
                    'album': tags.album,
                    'title': tags.title,
                    'duration': tags.duration,
                    'filename': file
                })
            playlist.append(entry)
        return playlist



class ControllerNamespace(BaseNamespace):
    def recv_message(self, data):
        controller.handleMessage(data)


class Application(object):
    def __init__(self):
        pass

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO'].strip('/')

        if path.startswith('socket.io'):
            socketio_manage(environ, {'': ControllerNamespace}, self.request)


if __name__ == '__main__':
    server = SocketIOServer(('0.0.0.0', 8080), Application(), resource='socket.io')

    controller = WebController(server)

    server.serve_forever()


