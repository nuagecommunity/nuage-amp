#!/usr/bin/env python
# encoding: utf-8

"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2015
@version: 0.0.1
"""

from time import sleep
from nuage_amp.utils.log import logger
from nuage_amp.utils.nuage import NuageConnection, NuageHTTPError, NuageResponse
from nuage_amp.utils.config import cfg
import keystoneclient.v2_0.client as ksclient
from neutronclient.v2_0 import client as neutronclient
from novaclient import client as novaclient
from sync import sync_subnets


def get_admin_nova_creds(tenant_name):
    return {'version': "2", 'username': cfg.get('openstack', 'admin_username'),
            'api_key': cfg.get('openstack', 'admin_password'), 'auth_url': cfg.get('openstack', 'auth_url'),
            'project_id': tenant_name, 'service_type': "compute"}


def get_keystone_creds():
    return {'username': cfg.get('openstack', 'admin_username'), 'password': cfg.get('openstack', 'admin_password'),
            'auth_url': cfg.get('openstack', 'auth_url'), 'tenant_name': "admin"}


def get_neutron_creds(user, pw, tenant):
    return {'username': user, 'password': pw, 'auth_url': cfg.get('openstack', 'auth_url'), 'tenant_name': tenant}


def keystone_tenant_exists(tenant_name):
    cr = get_keystone_creds()
    ks = ksclient.Client(**cr)
    try:
        if ks.tenants.find(name="{0:s}".format(tenant_name)):
            return True
        else:
            return False
    except:
        return False


def netpartition_exists(tenant_name):
    neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'), cfg.get('openstack', 'admin_password'),
                                      "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        if neutron.list_net_partitions(name=tenant_name)['net_partitions'][0]:
            return True
        else:
            return False
    except:
        return False


def delete_vms_in_tenant(tenant_name):
    logger.info("Deleting all VMs for tenant: {0:s}".format(tenant_name))
    nova_creds = get_admin_nova_creds(tenant_name)
    nova = novaclient.Client(**nova_creds)
    try:
        for server in nova.servers.list():
            logger.info("Deleting Server: {0:s}".format(server['id']))
            server.delete()
    except Exception, e:
        logger.error("|- ERROR deleting VM: {0:s}".format(server['id']))
        logger.error(repr(e))
    return


def delete_vsdobjects_in_tenant(tenant_name):
    logger.info("Deleting all VSD objects for tenant: {0:s}".format(tenant_name))
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'),
                         version=cfg.get('vsd', 'version'), port=cfg.get('vsd', 'port'))
    enterprise = nc.get("enterprises", filtertext="name == \"{0:s}\"".format(tenant_name)).obj()[0]
    # Get and delete all the active domains in the enterprise
    try:
        domains = nc.get("enterprises/{0:s}/domains".format(enterprise['ID'])).obj()
        # Delete each L3 domain
        for domain in domains:
            nc.put("domains/{0:s}".format(domain["ID"]), {"maintenanceMode": "ENABLED"})
            vports = nc.get("domains/{0:s}/vports".format(domain["ID"])).obj()
            for vport in vports:
                logger.info("VSD - Deleting vport: {0:s}".format(vport["ID"]))
                if vport["type"] == "BRIDGE":
                    logger.info("VSD - Deleting bridgeport")
                    try:
                        nc.delete(
                            "bridgeinterfaces/{0:s}".format(
                                nc.get("vports/{0:s}/bridgeinterfaces".format(vport["ID"])).obj()[0]["ID"]))
                    except Exception, e:
                        logger.info("VSD - no Bridgeinterface found")
                        logger.error(repr(e))
                if vport["type"] == "HOST":
                    logger.info("VSD - Deleting hostport interface")
                    try:
                        hostport = nc.get("vports/{0:s}/hostinterfaces".format(vport["ID"])).obj()
                        nc.delete("hostinterfaces/{0:s}".format(hostport[0]["ID"]))
                    except Exception, e:
                        logger.info("VSD - no host interface found")
                        logger.error(repr(e))
                sleep(2)
                alarms = nc.get("vports/{0:s}/alarms".format(vport["ID"])).obj()
                for alarm in alarms:
                    try:
                        nc.delete("alarms/{0:s}".format(alarm["ID"]))
                    except Exception, e:
                        logger.info("VSD - while deleting alarm")
                        logger.error(repr(e))
                nc.delete("vports/{0:s}".format(vport["ID"]))
            nc.delete("domains/{0:s}".format(domain["ID"]))
    except Exception, e:
        logger.error("VSD - while deleting domains")
        logger.error(repr(e))
        return 1

    # Get and delete all the active l2domains in the enterprise
    try:
        domains = nc.get("enterprises/{0:s}/l2domains".format(enterprise['ID'])).obj()
        # Delete each L2 domain
        for domain in domains:
            nc.put("l2domains/{0:s}".format(domain["ID"]), {"maintenanceMode": "ENABLED"})
            vports = nc.get("l2domains/{0:s}/vports".format(domain["ID"])).obj()
            for vport in vports:
                logger.info("VSD - Deleting l2vport: {0:s}".format(vport["ID"]))
                if vport["type"] == "BRIDGE":
                    logger.info("VSD - Deleting bridgeport")
                    try:
                        nc.delete(
                            "bridgeinterfaces/{0:s}".format(
                                nc.get("vports/{0:s}/bridgeinterfaces".format(vport["ID"])).obj()[0]["ID"]))
                    except Exception, e:
                        logger.info("VSD - no Bridgeinterface found")
                        logger.error(repr(e))
                if vport["type"] == "HOST":
                    logger.info("VSD - Deleting hostport interface")
                    try:
                        hostport = nc.get("vports/{0:s}/hostinterfaces".format(vport["ID"])).obj()
                        logger.info("VSD - Deleting Host interface: {0:s}".format(hostport[0]["ID"]))
                        nc.delete("hostinterfaces/{0:s}".format(hostport[0]["ID"]))
                    except Exception, e:
                        logger.info("VSD - no host interface found")
                        logger.error(repr(e))
                sleep(2)
                alarms = nc.get("vports/{0:s}/alarms".format(vport["ID"])).obj()
                for alarm in alarms:
                    try:
                        nc.delete("alarms/{0:s}".format(alarm["ID"]))
                    except Exception, e:
                        logger.error("VSD - deleting alarm")
                        logger.error(repr(e))
                nc.delete("vports/{0:s}".format(vport["ID"]))
            nc.delete("l2domains/{0:s}".format(domain["ID"]))
    except Exception, e:
        logger.error("VSD - while deleting l2domains")
        logger.error(repr(e))
        return 1
    logger.info("syncing")
    sync_subnets()
    return


def create_vsd_managed_tenant(tenant_name):
    logger.info("Creating VSD Managed Tenant: {0:s}".format(tenant_name))
    creds = get_keystone_creds()
    keystone = ksclient.Client(**creds)
    logger.info("Creating Keystone Tenant: {0:s}".format(tenant_name))
    try:
        if keystone_tenant_exists(tenant_name):
            logger.error("|- ERROR tenant {0:s} already exists in keystone".format(tenant_name))
            os_tenant = keystone.tenants.find(name="{0:s}".format(tenant_name))
        else:
            os_tenant = keystone.tenants.create(tenant_name="{0:s}".format(tenant_name),
                                                description="VSD Managed Openstack Tenant",
                                                enabled=True)
    except Exception, e:
        logger.error("|- ERROR creating tenant {0:s} in keystone".format(tenant_name))
        logger.error(repr(e))
    try:
        admin_role = keystone.roles.find(name='admin')
    except Exception, e:
        logger.error("|- ERROR finding admin role in keystone")
        logger.error(repr(e))
    try:
        os_admin = keystone.users.find(name=cfg.get('openstack', 'admin_username'))
    except Exception, e:
        logger.error("|- ERROR finding user {0:s} in keystone".format(cfg.get('openstack', 'admin_username')))
        logger.error(repr(e))
    try:
        logger.info("Adding admin role for user {0:s} in tenant {1:s} in keystone".format(
            cfg.get('openstack', 'admin_username'), tenant_name))
        keystone.roles.add_user_role(os_admin, admin_role, os_tenant)
    except Exception, e:
        logger.error("|- ERROR adding admin role for user {0:s} in tenant {1:s} in keystone".format(
            cfg.get('openstack', 'admin_username'), tenant_name))
        logger.error(repr(e))
    neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'), cfg.get('openstack', 'admin_password'),
                                      "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        logger.info("Creating Net-Partition: {0:s}".format(tenant_name))
        body_netpart = {
            "net_partition":
                {
                    "name": tenant_name
                }
        }
        neutron.create_net_partition(body=body_netpart)
    except Exception, e:
        logger.error("|- ERROR creating netpartition: {0:s}".format(tenant_name))
        logger.error(repr(e))
    logger.info("Finished Creating VSD Managed Tenant: {0:s}".format(tenant_name))


def delete_vsd_managed_tenant(tenant_name, force):
    logger.info("Deleting VSD Managed Tenant: {0:s}".format(tenant_name))
    creds = get_keystone_creds()
    keystone = ksclient.Client(**creds)
    if force:
        try:
            delete_vms_in_tenant(tenant_name)
        except Exception, e:
            logger.error("|- ERROR deleting VMs from tenant {0:s}".format(tenant_name))
            logger.error(repr(e))
        try:
            delete_vsdobjects_in_tenant(tenant_name)
        except Exception, e:
            logger.error("|- ERROR deleting VSD Objects from tenant {0:s}".format(tenant_name))
            logger.error(repr(e))
    if keystone_tenant_exists(tenant_name):
        try:
            logger.info("Deleting Keystone Tenant: {0:s}".format(tenant_name))
            os_tenant = keystone.tenants.find(name="{0:s}".format(tenant_name))
            os_tenant.delete()
        except Exception, e:
            logger.error("|- ERROR deleting tenant {0:s} in keystone".format(tenant_name))
            logger.error(repr(e))
            return 1
    else:
        logger.info("Keystone tenant {0:s} not present".format(tenant_name))
    neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'), cfg.get('openstack', 'admin_password'),
                                      "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        logger.info("Deleting Net-Partition: {0:s}".format(tenant_name))
        if not netpartition_exists(tenant_name):
            logger.error("|- Netpartition: {0:s} not found. Already deleted?".format(tenant_name))
            return
        netpart = neutron.list_net_partitions(name=tenant_name)['net_partitions'][0]
        neutron.delete_net_partition(netpart['id'])
    except Exception, e:
        logger.error("|- ERROR deleting netpartition: {0:s}".format(tenant_name))
        logger.error(repr(e))
    logger.info("Finished Deleting VSD Managed Tenant: {0:s}".format(tenant_name))


def list_vsd_managed_tenants():
    """Retrieves a list of the managed tenants in VSD"""
    # TODO: Improve list speed, nc.get("enterprises") is quite slow.
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'), version="v3_0",
                         port=cfg.get('vsd', 'port'))
    cr = get_keystone_creds()
    ks = ksclient.Client(**cr)
    try:
        tenants = ks.tenants.list()
    except:
        return "Could not connect to keystone."
    try:
        template = "{ID:40} | {name:20} | {description:30}"
        print template.format(ID="TENANT ID", name="TENANT NAME", description="TENANT DESCRIPTION")
        for ksi in tenants:
            for ent in nc.get("enterprises").obj():
                if ksi.name == ent["name"]:
                    print template.format(**ent)
    except:
        logger.error("Unable to get list of enterprises.")
