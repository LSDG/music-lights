import ConfigParser


class ConfigParserDefault(ConfigParser.SafeConfigParser):
    def get_def(self, section, key, default=None):
        try:
            return self.get(section, key)
        except ConfigParser.NoOptionError:
            return default
