from socketIO_client import SocketIO, BaseNamespace, transports
import logging
import inspect
import time

#transports.TIMEOUT_IN_SECONDS = 60
logging.basicConfig(level=logging.DEBUG)

currentSong = ''
songStart = None

def onLoop(self):
    print 'Looping!', songStart

    if songStart is not None:
        print 'Time:', time.time() - songStart
        if time.time() - songStart > 120:
            piSpace.emit('song finished', {'song': currentSong})

    return self._recv_packet()

transports._AbstractTransport._recv_packet = transports._AbstractTransport.recv_packet
transports._AbstractTransport.recv_packet = onLoop

class Namespace(BaseNamespace):

    def initialize(self):
        self.disconnected = False

    def on_connect(self):
        print 'Connected'

        if self.disconnected:
            global piSpace
            piSpace = socketIO.define(Namespace, '/rpi')

    def on_reconnect(self):
        print 'Re-connected'
        global piSpace
        piSpace = socketIO.define(Namespace, '/rpi')

    def on_event(self, event, *args):
        print 'Event:', event

    def on_heartbeat(self):
        super(Namespace, self).on_heartbeat()
        print 'Heartbeat'

    def on_list_songs(self, callback):
        print 'Got list songs', inspect.getsource(callback)
        playList = [
            {
                'title': 'Best Kept Secret',
                'artist': 'Skillet',
                'duration': 120,
                'filename': 'Skillet - Best Kept Secret.mp3'
            },
            {
                'title': 'Welcome Home',
                'artist': 'Coheed and Cambria',
                'duration': 20,
                'filename': 'Home.mp3'
            },
            {
                'title': "Winter Wizard (Instrumental)",
                'artist': "Trans-Siberian Orchestra",
                'duration': 20,
                'filename': "TSO - Winter Wizard.mp3"
            },
        ]
        callback(playList)

    def on_play_next(self, song, callback):
        print 'Play next:', song
        global currentSong, songStart
        currentSong = song['song']
        songStart = time.time()
        callback()

    def on_disconnect(self):
        self.disconnected = True
        print "We've lost the server!"

socketIO = SocketIO('localhost', 8080, Namespace)
piSpace = socketIO.define(Namespace, '/rpi')
piSpace.emit('test', 'bob')
socketIO.wait(120)
