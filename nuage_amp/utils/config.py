#!/usr/bin/env python
"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2014
@version: 0.0.1
"""

import ConfigParser
import os
from log import logger


def readconfig(path):
    if not os.path.isfile(path):
        raise ValueError('Invalid config file: {0:s}'.format(path))
    logger.info("Reading config file from {0:s}".format(path))
    cfg.read(path)

cfg = ConfigParser.ConfigParser()
