import os
import json
import logging

class Config:
    _DEFAULTS = {
        'DOWNLOAD_DIR': './downloads',
        'AUDIO_DOWNLOAD_DIR': './audio',
        'TEMP_DIR': './temp',
        'STATE_DIR': './state',
        'YTDL_OPTIONS': '{}',
        'HOST': '0.0.0.0',
        'PORT': '8081',
        'DATABASE': './downloads.db',  # Add this line
    }

    def __init__(self):
        for key, value in self._DEFAULTS.items():
            setattr(self, key, os.getenv(key, value))
        try:
            self.YTDL_OPTIONS = json.loads(self.YTDL_OPTIONS)
        except json.JSONDecodeError:
            logging.error('Invalid YTDL_OPTIONS format')
            self.YTDL_OPTIONS = {}

config = Config()
