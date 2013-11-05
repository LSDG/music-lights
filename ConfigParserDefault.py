import ConfigParser


class ConfigParserDefault(ConfigParser.SafeConfigParser):
    def get_def(self, section, key, default=None):
        """Get an option value from the named section, returning the given default if either the option or section is
        not present.

        """
        try:
            return self.get(section, key)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default
