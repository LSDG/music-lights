from ConfigParserDefault import ConfigParserDefault
import os


class SongConfig(object):
    def __init__(self, config):
        self.defaultThresholds = map(float, config.get_def('spectrum', 'thresholds').split(','))
        self.defaultOffThresholds = map(float, config.get_def('spectrum', 'offThresholds').split(','))

        self.defaultOrder = map(int, config.get_def('lights', 'channelOrder').split(','))

        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

    def loadSongSettings(self, filename, *args):
        self.frequencyThresholds = self.defaultThresholds
        self.frequencyOffThresholds = self.defaultOffThresholds
        self.frequencyBandOrder = self.defaultOrder

        iniPath = filename + '.ini'
        if os.path.exists(iniPath):
            cp = ConfigParserDefault()
            cp.read([iniPath])

            self.frequencyThresholds = map(float, cp.get_def('spectrum', 'thresholds').split(','))
            self.frequencyOffThresholds = map(float, cp.get_def('spectrum', 'offThresholds').split(','))

            self.frequencyBandOrder = map(int, cp.get_def('lights', 'channelOrder').split(','))

