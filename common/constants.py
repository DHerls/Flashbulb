import os
import pathlib


class SemanticVersion:
    """Helper class for comparing semantic versions.
    
    https://semver.org/
    """

    def __init__(self, version):
        self.major, self.minor, self.patch = version.split('.')
        self.major = int(self.major)
        self.minor = int(self.minor)
        self.patch = int(self.patch)

    def __lt__(self, other):
        if self.major < other.major:
            return True
        elif self.major == other.major:
            if self.minor < other.minor:
                return True
            elif self.minor == other.minor:
                if self.patch < other.patch:
                    return True
        return False

    def __eq__(self, other):
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __str__(self):
        return '{}.{}.{}'.format(self.major, self.minor, self.patch)


FLASHBULB_BUCKET_PREFIX = 'flashbulb-'

ENTITIES = {
    "screenshot": {
        "version": SemanticVersion('0.7.1'),
        "layers": [
            "chromium"
        ],
        "type": "function"
    },
    "analyze": {
        "version": SemanticVersion('0.2.4'),
        "layers": [
            "wappalyzer"
        ],
        "type": "function"
    },
    "chromium": {
        "version": SemanticVersion('3.1.1'),
        "type": "layer"
    },
    "wappalyzer": {
        "version": SemanticVersion('6.0.13'),
        "type": "layer"
    }
}

FLASHBULB_DIR = pathlib.Path(__file__).parent.parent.absolute()
