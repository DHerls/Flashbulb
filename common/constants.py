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

SCREENSHOT_LAMBDA_NAME = 'Flashbulb--Screenshot'
SCREENSHOT_LAMBDA_VERSION = SemanticVersion('0.6.2')
SCREENSHOT_S3_KEY = 'screenshot/{version}/function.zip'.format(
    version=str(SCREENSHOT_LAMBDA_VERSION))

CHROMIUM_LAYER_NAME = 'Flashbulb--HeadlessChromium'
CHROMIUM_LAYER_VERSION = SemanticVersion('3.1.1')
CHROMIUM_S3_KEY = 'chromium/{version}/layer.zip'.format(version=str(CHROMIUM_LAYER_VERSION))

TEMP_FILES_DIRECTORY = os.path.join(os.getcwd(), '_temp')
