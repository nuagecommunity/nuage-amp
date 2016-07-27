#!/usr/bin/env python
# encoding: utf-8

"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2014
@version: 0.0.1
"""

from nuage_amp.utils.nuage import NuageConnection, NuageHTTPError, NuageResponse
from nuage_amp.utils.log import logger
from nuage_amp.utils.config import cfg
import socket


def create(url, enterprise_name):
    logger.info("Creating/updating Network Macro from url: %s" % url)
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'),
                         version=cfg.get('vsd', 'version'), port=cfg.get('vsd', 'port'))
    try:
        ip = socket.gethostbyname(url)
    except:
        logger.error("Error looking up hostname or hostname cannot be found")
        return 1
    try:
        enterprise = nc.get("enterprises", filtertext="name == \"%s\"" % enterprise_name).obj()[0]
    except:
        logger.error("Error getting enterprise %s" % enterprise_name)
        return 1
    if not enterprise:
        logger.error("No enterprise found with name %s" % enterprise_name)
        return 1
    try:
        macro = nc.get("enterprises/%s/enterprisenetworks" % enterprise['ID'],
                       filtertext="name == \"%s\"" % url.replace(".", "-")).obj()
    except:
        logger.error("Error getting existing macros from enterprise %s" % enterprise_name)
        return 1
    if not macro:
        logger.info("Network Macro for %s does not exist, creating a new one." % url)
        try:
            nc.post("enterprises/%s/enterprisenetworks" % enterprise['ID'],
                    {"IPType": "IPV4",
                     "address": ip,
                     "name": url.replace(".", "-"),
                     "netmask": "255.255.255.255"})
            logger.info("Network Macro created for %s with ip:%s." % (url, ip))
            return 0
        except:
            logger.error("Error creating new Network Macro for %s" % url)
            return 1
    else:
        if not macro[0]['address'] == ip:
            logger.info("Network Macro for %s does exists, but address is not correct.(current:%s | new:%s)" % (
                url, macro[0]['address'], ip))
            try:
                nc.put("enterprisenetworks/%s" % macro[0]['ID'],
                       {"address": ip,
                        "netmask": "255.255.255.255"})
                logger.info("Network Macro for %s updated with ip:%s." % (url, ip))
                return 0
            except:
                logger.error("Error updating Network Macro for %s" % url)
                return 1
        else:
            logger.info("Network Macro for %s does exists and address is correct." % url)
            return 0


def delete(url, enterprise_name):
    logger.info("Deleting Network Macro with url: %s" % url)
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'), version="v3_0",
                         port=cfg.get('vsd', 'port'))
    try:
        enterprise = nc.get("enterprises", filtertext="name == \"%s\"" % enterprise_name).obj()[0]
    except:
        logger.error("Error getting enterprise %s" % enterprise_name)
        return 1
    if not enterprise:
        logger.error("No enterprise found with name %s" % enterprise_name)
        return 1
    try:
        macro = nc.get("enterprises/%s/enterprisenetworks" % enterprise['ID'],
                       filtertext="name == \"%s\"" % url.replace(".", "-")).obj()
    except:
        logger.error("Error getting existing macros %s" % enterprise_name)
        return 1
    if not macro:
        logger.info("Network Macro for %s does not exist" % url)
        return 0
    else:
        try:
            nc.delete("enterprisenetworks/%s" % macro[0]['ID'])
            logger.info("Deleted Network Macro for %s." % url)
            return 0
        except:
            logger.error("Error deleting Network Macro for %s" % url)
            return 1
