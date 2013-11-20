from __future__ import print_function
from multiprocessing import Process, Queue
from Queue import Empty
import sys
import hsaudiotag.auto
import time
import logging

from socketIO_client import SocketIO, BaseNamespace, transports, ConnectionError

import player


files = sys.argv[1:]

logging.basicConfig(level=logging.DEBUG)


class HeartbeatListener(BaseNamespace):
    def initialize(self):
        self.lastHeartbeat = time.time()
        self.disconnected = True

    def on_connect(self):
        self.disconnected = False

    def on_heartbeat(self):
        self.lastHeartbeat = time.time()

    def onLoop(self):
        if time.time() - self.lastHeartbeat > 70 and not self.disconnected:
            print('HeartbeatListener: Heartbeat timeout (>70)')
            self.disconnected = True
            socketIO._namespace_by_path['/rpi'].on_disconnect()


class WebController(BaseNamespace):
    def on_list_songs(self, callback):
        print('Got list songs request')
        playlist = self.generatePlaylist()
        callback(playlist)

    def on_play_next(self, data, callback):
        print('WebController: Play next:', data)
        self.controllerQueue.put(('play next', data['song']))
        callback()

    def on_stop(self):
        self.controllerQueue.put(('stop', ''))

    def on_disconnect(self):
        print('WebController disconnected')
        self.controllerQueue.put(('lost connection', ''))

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

    def onLoop(self):
        try:
            msg = self.playerQueue.get_nowait()
            print('Msg from player:', msg)
            self.emit('song finished', {'song': msg['song']})
        except Empty:
            pass


def buildSocket(controllerQueue):
    try:
        socketIO = SocketIO('localhost', 8080, HeartbeatListener, wait_for_connection=False)
        return socketIO
    except ConnectionError:
        controllerQueue.put(('no connection', ''))
        failTime = time.time()
        while True:
            if time.time() - failTime > 5:
                return buildSocket(controllerQueue)


if __name__ == '__main__':
    playerQueue = Queue()
    controllerQueue = Queue()
    playerProcess = Process(target=player.runPlayerProcess, args=(playerQueue, controllerQueue, files))
    playerProcess.start()

    socketIO = buildSocket(controllerQueue)

    controller = socketIO.define(WebController, '/rpi')
    controller.playerQueue = playerQueue
    controller.controllerQueue = controllerQueue

    def onLoop(self):
        global socketIO
        for item in socketIO._namespace_by_path.itervalues():
            item.onLoop()

        return self._recv_packet()

    transports._AbstractTransport._recv_packet = transports._AbstractTransport.recv_packet
    transports._AbstractTransport.recv_packet = onLoop

    socketIO.wait()
