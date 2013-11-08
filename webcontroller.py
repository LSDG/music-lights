from multiprocessing import Process, Queue
import os
from Queue import Full as QueueFull
import sys
import hsaudiotag.auto
import json

from socketIO_client import SocketIO, BaseNamespace, transports

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

    def on_play_next(self, data, callback):
        print 'Play next:', data
        self.controllerQueue.put(data['song'])
        callback()

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

    def readQueue(self):
        msg = self.playerQueue.get_nowait()
        print 'Msg from player:', msg
        self.emit('song finished', {'song': msg['song']})


if __name__ == '__main__':
    socketIO = SocketIO('localhost', 8080)

    controller = socketIO.define(WebController, '/rpi')

    def onLoop(self):
        print 'Looping!'
        controller.readQueue()
        return self._recv_packet()

    transports._AbstractTransport._recv_packet = transports._AbstractTransport.recv_packet
    transports._AbstractTransport.recv_packet = onLoop

    socketIO.wait()
