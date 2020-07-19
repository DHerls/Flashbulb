import os


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


FUNCTIONS = {
    "screenshot": {
        "version": SemanticVersion('0.7.1'),
        "layers": [
            "chromium"
        ],
        "runtime": "nodejs12.x",
        'handler': 'index.handler',
        'timeout': 300,
        'memory': 2048
    },
    "analyze": {
        "version": SemanticVersion('0.1.2'),
        "layers": [
            "wappalyzer"
        ],
        "runtime": 'nodejs12.x',
        "handler": 'index.handler',
        'timeout': 60,
        'memory': 500
    }
}


LAYERS = {
    "chromium": {
        "version": SemanticVersion('3.1.1'),
        "runtimes": [
            'nodejs10.x', 'nodejs12.x'
        ]
    },
    "wappalyzer": {
        "version": SemanticVersion('6.0.13'),
        "runtimes": [
            'nodejs10.x', 'nodejs12.x'
        ]
    }
}

TEMP_FILES_DIRECTORY = os.path.join(os.getcwd(), '_temp')
