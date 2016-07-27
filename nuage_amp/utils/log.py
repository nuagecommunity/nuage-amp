#!/usr/bin/env python
"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2014
@version: 0.0.1
"""

import logging
import logging.handlers
import sys
import os

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}


def setlogpath(path, logconfig=None):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    fileh = logging.FileHandler(path, 'a')
    if logconfig and logconfig.has_section('logging'):
        if logconfig.has_option('logging', 'rotate_logfiles'):
            enableRotate = logconfig.getboolean('logging', 'rotate_logfiles')
            if enableRotate:
                # if not set, use default of 10 megabytes and 5 backups
                maxsize = 10  # maxsize is in mega bytes.
                backups = 5
                if logconfig.has_option('logging', 'maxsize'):
                    maxsize = int(logconfig.get('logging', 'maxsize'))
                if logconfig.has_option('logging', 'backups'):
                    backups = int(logconfig.get('logging', 'backups'))
                fileh = logging.handlers.RotatingFileHandler(path, 'a', maxBytes=maxsize * 1000000, backupCount=backups)

    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
    fileh.setFormatter(formatter)
    for hdlr in logger.handlers:
        logger.removeHandler(hdlr)
    logger.addHandler(fileh)
    logger.propagate = False


def setloglevel(log_level):
    parsed_log_level = LEVELS.get(log_level.lower(), logging.NOTSET)
    if not parsed_log_level:
        raise ValueError('Invalid log level: %s' % log_level)
    logger.info("Changing logging level to %s" % parsed_log_level)
    logger.setLevel(parsed_log_level)

logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
logger = logging.getLogger('nuage-amp')
logger.info("Logging started with logging level ERROR")
