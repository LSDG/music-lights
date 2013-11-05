from socketIO_client import SocketIO, BaseNamespace, transports
import logging
import inspect

transports.TIMEOUT_IN_SECONDS = 60
logging.basicConfig(level=logging.DEBUG)

class Namespace(BaseNamespace):

    def initialize(self):
        self.path = '/rpi'

    def on_connect(self):
        print '[Connected]'

    def on_event(self, event, *args):
        print 'Event:', event

    def on_heartbeat(self):
        print 'Heartbeat'

    def on_list_songs(self, callback):
        print 'Got list songs', inspect.getsource(callback)
        playList = [
            {
                'title': "Winter Wizard (Instrumental)",
                'artist': "Trans-Siberian Orchestra",
                'duration': 185,
                'filename': "TSO - Winter Wizard.mp3"
            }
        ]
        callback(playList)

socketIO = SocketIO('localhost', 8080, Namespace)
piSpace = socketIO.define(Namespace, '/rpi')
piSpace.emit('test', 'bob')
socketIO.wait()
