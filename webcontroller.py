from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys
import hsaudiotag.auto
import json

from socketIO_client import SocketIO, BaseNamespace

import player

files = sys.argv[1:]

class WebController(BaseNamespace):
    def initialize(self):
        self.playerQueue = Queue()
        self.controllerQueue = Queue()

        self.playerProcess = Process(target=player.runPlayerProcess, args=(self.playerQueue, self.controllerQueue))

    def on_list_songs(self):
        print 'Got list songs request'
        playlist = self.generatePlaylist()
        self.emit('list songs', playlist)

    def on_play_next(self, song):
        print 'Play next:', song
        self.controller.controllerQueue.put(song)

    def generatePlaylist(self):
        playlist = list()
        for song in files:
            tags = hsaudiotag.auto.File(song)
            if not tags.valid:
                entry = json.dumps({
                    'title': song,
                    'filename': song
                })
            else:
                entry = json.dumps({
                    'artist': tags.artist,
                    'album': tags.album,
                    'title': tags.title,
                    'duration': tags.duration,
                    'filename': song
                })
            playlist.append(entry)
        return playlist

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


