#!/usr/bin/env python
# encoding: utf-8

"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2014
@version: 0.0.1
"""

from nuage_amp.utils.log import logger
from nuage_amp.utils.nuage import NuageConnection, NuageHTTPError, NuageResponse
from nuage_amp.utils.config import cfg


def audit_vports():
    logger.info("Auditing vPorts")
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'),
                         version=cfg.get('vsd', 'version'), port=cfg.get('vsd', 'port'))
    try:
        dead_vms = nc.get("vms", filtertext="hypervisorIP == \"FFFFFF\"").obj()
        for vm in dead_vms:
            logger.info("Deleting orphaned VM with ID: {0:s}".format(vm['ID']))
            try:
                nc.delete("vms/{0:s}".format(vm['ID']))
            except:
                logger.error("Error deleting orphaned VM with ID: {0:s}".format(vm['ID']))
    except:
        logger.error("Error getting orphaned VMs")

    logger.info("Finished Auditing vPorts")
