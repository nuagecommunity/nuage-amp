#!/usr/bin/env python
# @author: Philippe Jeurissen
# @copyright: Alcatel-Lucent 2014
# @version: 0.0.1

import ConfigParser
import os
from log import logger


def readconfig(path):
    if not os.path.isfile(path):
        raise ValueError('Invalid config file: %s' % path)
    logger.info("Reading config file from %s" % path)
    cfg.read(path)

cfg = ConfigParser.ConfigParser()
