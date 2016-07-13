from __future__ import (
    unicode_literals,
    absolute_import,
    print_function,
    division,
    )
str = type('')


class Settings(object):
    def __init__(self, path):
        self.path = path

class RTIMU(object):
    def __init__(self, settings):
        self.settings = settings

class RTPressure(object):
    def __init__(self, settings):
        self.settings = settings

class RTHumidity(object):
    def __init__(self, settings):
        self.settings = settings

