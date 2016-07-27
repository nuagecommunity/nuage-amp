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
    logger.info("Creating/updating Network Macro from url: {0}".format(url))
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'),
                         version=cfg.get('vsd', 'version'), port=cfg.get('vsd', 'port'))
    try:
        ip = socket.gethostbyname(url)
    except:
        logger.error("Error looking up hostname or hostname cannot be found")
        return 1
    try:
        enterprise = nc.get("enterprises", filtertext="name == \"{0}\"".format(enterprise_name)).obj()[0]
    except:
        logger.error("Error getting enterprise {0}".format(enterprise_name))
        return 1
    if not enterprise:
        logger.error("No enterprise found with name {0}".format(enterprise_name))
        return 1
    try:
        macro = nc.get("enterprises/{0}/enterprisenetworks".format(enterprise['ID']),
                       filtertext="name == \"{0}\"".format(url.replace(".", "-"))).obj()
    except:
        logger.error("Error getting existing macros from enterprise {0}".format(enterprise_name))
        return 1
    if not macro:
        logger.info("Network Macro for {0} does not exist, creating a new one.".format(url))
        try:
            nc.post("enterprises/{0}/enterprisenetworks".format(enterprise['ID']),
                    {"IPType": "IPV4",
                     "address": ip,
                     "name": url.replace(".", "-"),
                     "netmask": "255.255.255.255"})
            logger.info("Network Macro created for {0} with ip:{1}.".format(url, ip))
            return 0
        except:
            logger.error("Error creating new Network Macro for {0}".format(url))
            return 1
    else:
        if not macro[0]['address'] == ip:
            logger.info(
                "Network Macro for {0} does exists, but address is not correct.(current:{1} | new:{2})".format(
                    url, macro[0]['address'], ip))
            try:
                nc.put("enterprisenetworks/{0}".format(macro[0]['ID']),
                       {"address": ip,
                        "netmask": "255.255.255.255"})
                logger.info("Network Macro for {0} updated with ip:{1}.".format(url, ip))
                return 0
            except:
                logger.error("Error updating Network Macro for {0}".format(url))
                return 1
        else:
            logger.info("Network Macro for {0} does exists and address is correct.".format(url))
            return 0


def delete(url, enterprise_name):
    logger.info("Deleting Network Macro with url: {0}".format(url))
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'), version="v3_0",
                         port=cfg.get('vsd', 'port'))
    try:
        enterprise = nc.get("enterprises", filtertext="name == \"{0}\"".format(enterprise_name)).obj()[0]
    except:
        logger.error("Error getting enterprise {0}".format(enterprise_name))
        return 1
    if not enterprise:
        logger.error("No enterprise found with name {0}".format(enterprise_name))
        return 1
    try:
        macro = nc.get("enterprises/{0}/enterprisenetworks".format(enterprise['ID']),
                       filtertext="name == \"{0}\"".format(url.replace(".", "-"))).obj()
    except:
        logger.error("Error getting existing macros {0}".format(enterprise_name))
        return 1
    if not macro:
        logger.info("Network Macro for {0} does not exist".format(url))
        return 0
    else:
        try:
            nc.delete("enterprisenetworks/{0}".format(macro[0]['ID']))
            logger.info("Deleted Network Macro for {0}.".format(url))
            return 0
        except:
            logger.error("Error deleting Network Macro for {0}".format(url))
            return 1
