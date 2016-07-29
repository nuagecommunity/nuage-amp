#!/usr/bin/env python
"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2014
"""

import ConfigParser
import os
from log import logger


def readconfig(path):
    if not os.path.isfile(path):
        raise ValueError('Invalid config file: {0}'.format(path))
    logger.info("Reading config file from {0}".format(path))
    cfg.read(path)

cfg = ConfigParser.ConfigParser()
