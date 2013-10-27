from ConfigParserDefault import ConfigParserDefault
import os


class SongConfig(object):
    def __init__(self, config):
        # Slow the light state changes down to every 0.05 seconds.
        self.delayBetweenUpdates = float(config.get_def('main', 'delayBetweenUpdates', 0.05))

        self.defaultThresholds = map(float, config.get_def('spectrum', 'thresholds').split(','))
        self.defaultOffThresholds = map(float, config.get_def('spectrum', 'offThresholds').split(','))
        self.defaultOrder = map(int, config.get_def('spectrum', 'channelOrder').split(','))

        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

    def loadSongSettings(self, filename):
        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

        iniPath = filename + '.ini'
        if os.path.exists(iniPath):
            cp = ConfigParserDefault()
            cp.read([iniPath])

            self.frequencyThresholds = map(float, cp.get_def('spectrum', 'thresholds').split(','))
            self.frequencyOffThresholds = map(float, cp.get_def('spectrum', 'offThresholds').split(','))
            self.frequencyBandOrder = map(int, cp.get_def('spectrum', 'channelOrder').split(','))

