import ConfigParser
import os


class SongConfig(object):
    def __init__(self, config):
        # Slow the light state changes down to every 0.05 seconds.
        self.delayBetweenUpdates = float(config.get('main', 'delayBetweenUpdates', 0.05))

        self.defaultThresholds = map(float, config.get('spectrum', 'thresholds').split(','))
        self.defaultOffThresholds = map(float, config.get('spectrum', 'offThresholds').split(','))
        self.defaultOrder = map(int, config.get('spectrum', 'channelOrder').split(','))

        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

    def loadSongSettings(self, filename):
        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

        iniPath = filename + '.ini'
        if os.path.exists(iniPath):
            cp = ConfigParser.SafeConfigParser()
            cp.read([iniPath])

            self.frequencyThresholds = map(float, cp.get('spectrum', 'thresholds').split(','))
            self.frequencyOffThresholds = map(float, cp.get('spectrum', 'offThresholds').split(','))
            self.frequencyBandOrder = map(int, cp.get('spectrum', 'channelOrder').split(','))

