from multiprocessing import Process, Queue
from Queue import Empty
import sys
import hsaudiotag.auto
import logging

from socketIO_client import SocketIO, BaseNamespace, transports

import player

files = sys.argv[1:]

logging.basicConfig(level=logging.DEBUG)

class WebController(BaseNamespace):
    def initialize(self):
        self.disconnected = False
        self.playerQueue = Queue()
        self.controllerQueue = Queue()

        self.playerProcess = Process(target=player.runPlayerProcess, args=(self.playerQueue, self.controllerQueue, files))
        self.playerProcess.start()

    def on_connect(self):
        if self.disconnected:
            self.disconnected = False
            global controller
            controller = socketIO.define(WebController, '/rpi')

    def on_list_songs(self, callback):
        print 'Got list songs request'
        playlist = self.generatePlaylist()
        callback(playlist)

    def on_play_next(self, data, callback):
        print 'WebController: Play next:', data
        self.controllerQueue.put(('play next', data['song']))
        callback()

    def on_stop(self):
        self.controllerQueue.put(('stop', ''))

    def generatePlaylist(self):
        playlist = list()
        for song in files:
            tags = hsaudiotag.auto.File(song)
            if not tags.valid:
                entry = {
                    'title': song,
                    'filename': song
                }
            else:
                entry = {
                    'artist': tags.artist,
                    'album': tags.album,
                    'title': tags.title,
                    'duration': tags.duration,
                    'filename': song
                }
            playlist.append(entry)
        return playlist

    def readQueue(self):
        try:
            msg = self.playerQueue.get_nowait()
            print 'Msg from player:', msg
            self.emit('song finished', {'song': msg['song']})
        except Empty:
            pass

    def on_disconnect(self):
        self.disconnected = True
        self.controllerQueue.put(('lost connection', ''))


if __name__ == '__main__':
    socketIO = SocketIO('localhost', 8080)

    controller = socketIO.define(WebController, '/rpi')

    def onLoop(self):
        global controller
        controller.readQueue()
        return self._recv_packet()

    transports._AbstractTransport._recv_packet = transports._AbstractTransport.recv_packet
    transports._AbstractTransport.recv_packet = onLoop

    socketIO.wait()
