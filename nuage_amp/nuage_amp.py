#!/usr/bin/python
# @ageuthor: Philippe Jeurissen
# @copyright: Alcatel-Lucent 2014
# @version: 0.0.2
"""
Usage:
  nuage-amp sync [--once] [options]
  nuage-amp audit-vports [options]
  nuage-amp network-macro-from-url (create|delete) <url> <enterprise> [options]
  nuage-amp vsdmanaged-tenant (create|delete) <name> [--force] [options]
  nuage-amp (-h | --help)

Options:
  -h --help              Show this screen
  -v --version           Show version
  --log-file=<file>      Log file location
  --config-file=<file>   Configuration file location [default: /etc/nuage-amp/nuage-amp.conf]
Sync Options:
  --once                 Run the sync only once
Tenant Operations:
  --force                Forces tenant deletion. Will remove existing VMs and VSD objects(domains,subnets)

"""
from utils.config import cfg, readconfig
from utils.log import logger, setlogpath, setloglevel
from operations import *
from docopt import docopt
import time
import sys


def getargs():
    return docopt(__doc__, version="nuage-amp 0.1.1")


def main(args):
    try:
        readconfig(args['--config-file'])
    except Exception, e:
        logger.error("Error reading config file from location: %s" % args['--config-file'])
        logger.error(str(e))
        sys.exit(1)

    if args['--log-file']:
        try:
            setlogpath(args['--log-file'])
        except Exception, e:
            logger.error("Error setting log location: %s" % args['--log-file'])
            logger.error(str(e))
            sys.exit(1)

    if cfg.has_option('logging', 'loglevel'):
        try:
            setloglevel(cfg.get('logging', 'loglevel'))
        except Exception, e:
            logger.error("Error setting logging level to %s" % cfg.get('logging', 'loglevel'))
            logger.error(str(e))

    if args['sync']:
        if args['--once']:
            sync.sync_subnets()
        else:
            while True:
                sync.sync_subnets()
                time.sleep(10)

    elif args['audit-vports']:
        audit_vport.audit_vports()

    elif args['network-macro-from-url']:
        if args['create']:
            nw_macro.create(args['<url>'], args['<enterprise>'])
        elif args['delete']:
            nw_macro.delete(args['<url>'], args['<enterprise>'])
    elif args['vsdmanaged-tenant']:
        if args['create']:
            tenant.create_vsd_managed_tenant(args['<name>'])
        elif args['delete']:
            tenant.delete_vsd_managed_tenant(args['<name>'], args['--force'])


if __name__ == "__main__":
    main(getargs())
