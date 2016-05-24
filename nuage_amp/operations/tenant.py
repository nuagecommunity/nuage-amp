#!/usr/bin/env python
# encoding: utf-8

# Created on 2015-03-06
# 
# @author: Philippe Jeurissen
# @copyright: Alcatel-Lucent 2015
# @version: 0.0.1

from nuage_amp.utils.log import logger
from nuage_amp.utils.nuage import NuageConnection, NuageHTTPError, NuageResponse
from nuage_amp.utils.config import cfg
import keystoneclient.v2_0.client as ksclient
from neutronclient.v2_0 import client as neutronclient
from novaclient import client as novaclient
from sync import sync_subnets

def get_admin_nova_creds(tenant_name):
    d = {}
    d['version'] = "2"
    d['username'] = cfg.get('openstack','admin_username')
    d['api_key'] = cfg.get('openstack','admin_password')
    d['auth_url'] = cfg.get('openstack','auth_url')
    d['project_id'] = tenant_name
    d['service_type'] = "compute"
    return d

def get_keystone_creds():
    d = {}
    d['username'] = cfg.get('openstack','admin_username')
    d['password'] = cfg.get('openstack','admin_password')
    d['auth_url'] = cfg.get('openstack','auth_url')
    d['tenant_name'] = "admin"
    return d

def get_neutron_creds(user,pw, tenant):
    d = {}
    d['username'] = user
    d['password'] = pw
    d['auth_url'] = cfg.get('openstack','auth_url')
    d['tenant_name'] = tenant
    return d

def keystone_tenant_exists(tenant_name):
    cr = get_keystone_creds()
    ks = ksclient.Client(**cr)
    try:
        if ks.tenants.find(name="%s" % tenant_name):
            return True
        else:
            return False
    except:
        return False

def netpartition_exists(tenant_name):
    neutron_creds = get_neutron_creds(cfg.get('openstack','admin_username'), cfg.get('openstack','admin_password'), "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        if neutron.list_net_partitions(name=tenant_name)['net_partitions'][0]:
            return True
        else:
            return False
    except:
        return False

def delete_vms_in_tenant(tenant_name):
    logger.info("Deleting all VMs for tenant: %s" % tenant_name)
    nova_creds = get_admin_nova_creds(tenant_name)
    nova = novaclient.Client(**nova_creds)
    try:
        for server in nova.servers.list():
            logger.info("Deleting Server: %s" % server['id'])
            server.delete()
    except Exception, e:
        logger.error("|- ERROR deleting VM: %s" % server['id'])
        logger.error(repr(e))
    return

def delete_vsdobjects_in_tenant(tenant_name):
    logger.info("Deleting all VSD objects for tenant: %s" % tenant_name)
    nc = NuageConnection(cfg.get('vsd','hostname'), enterprise=cfg.get('vsd','enterprise'), username=cfg.get('vsd','username'), password=cfg.get('vsd','password'), version=cfg.get('vsd','version'), port=cfg.get('vsd','port'))
    enterprise = nc.get("enterprises",filtertext="name == \"%s\"" % tenant_name).obj()[0]
    ### Get and delete all the active domains in the enterprise
    try:
        domains = nc.get("enterprises/%s/domains" % enterprise['ID']).obj()
        #Delete each L3 domain
        for domain in domains:
            nc.put("domains/%s" % domain["ID"],{"maintenanceMode": "ENABLED"})
            vports = nc.get("domains/%s/vports" % domain["ID"]).obj()
            for vport in vports:
                logger.info("VSD - Deleting vport: %s" % vport["ID"])
                if vport["type"] == "BRIDGE":
                    logger.info("VSD - Deleting bridgeport")
                    try:
                        nc.delete("bridgeinterfaces/%s" %(nc.get("vports/%s/bridgeinterfaces" % vport["ID"]).obj()[0]["ID"]))
                    except Exception, e:
                        logger.info("VSD - no Bridgeinterface found")
                        logger.error(repr(e))
                if vport["type"] == "HOST":
                    logger.info("VSD - Deleting hostport interface")
                    try:
                        hostport = nc.get("vports/%s/hostinterfaces" % vport["ID"]).obj()
                        nc.delete("hostinterfaces/%s" % hostport[0]["ID"])
                    except Exception, e:
                        logger.info("VSD - no host interface found")
                time.sleep(2)
                alarms = nc.get("vports/%s/alarms" % vport["ID"]).obj()
                for alarm in alarms:
                   try:
                      nc.delete("alarms/%s" % alarm["ID"])
                   except Exception, e:
                      logger.info("VSD - while deleting alarm")
                nc.delete("vports/%s" % vport["ID"])
            nc.delete("domains/%s" % domain["ID"])
    except Exception, e:
        result = 1
        logger.error("VSD - while deleting domains")
        logger.error(repr(e))
        
    ### Get and delete all the active l2domains in the enterprise
    try:
        domains = nc.get("enterprises/%s/l2domains" % enterprise['ID']).obj()
        #Delete each L2 domain
        for domain in domains:
            nc.put("l2domains/%s" % domain["ID"],{"maintenanceMode": "ENABLED"})
            vports = nc.get("l2domains/%s/vports" % domain["ID"]).obj()
            for vport in vports:
                logger.info("VSD - Deleting l2vport: %s" % vport["ID"])
                if vport["type"] == "BRIDGE":
                    logger.info("VSD - Deleting bridgeport")
                    try:
                        nc.delete("bridgeinterfaces/%s" %(nc.get("vports/%s/bridgeinterfaces" % vport["ID"]).obj()[0]["ID"]))
                    except Exception, e:
                        logger.info("VSD - no Bridgeinterface found")
                        logger.error(repr(e))
                if vport["type"] == "HOST":
                    logger.info("VSD - Deleting hostport interface")
                    try:
                        hostport = nc.get("vports/%s/hostinterfaces" % vport["ID"]).obj()
                        logger.info("VSD - Deleting Host interface: %s" % hostport[0]["ID"])
                        nc.delete("hostinterfaces/%s" % hostport[0]["ID"])
                    except Exception, e:
                        logger.info("VSD - no host interface found")
                        logger.error(repr(e))
                time.sleep(2)
                alarms = nc.get("vports/%s/alarms" % vport["ID"]).obj()
                for alarm in alarms:
                   try:
                      nc.delete("alarms/%s" % alarm["ID"])
                   except Exception, e:
                      logger.error("VSD - deleting alarm")
                      logger.error(repr(e))
                nc.delete("vports/%s" % vport["ID"])
            nc.delete("l2domains/%s" % domain["ID"])
    except Exception, e:
        logger.error("VSD - while deleting l2domains")
        logger.error(repr(e))
        return 1
    logger.info("syncing")
    sync_subnets()
    return

def create_vsd_managed_tenant(tenant_name):
    logger.info("Creating VSD Managed Tenant: %s" % tenant_name)
    creds = get_keystone_creds()
    keystone = ksclient.Client(**creds)
    logger.info("Creating Keystone Tenant: %s" % tenant_name)
    try:
        if keystone_tenant_exists(tenant_name):
            logger.error("|- ERROR tenant %s already exists in keystone" % tenant_name)
            os_tenant = keystone.tenants.find(name="%s" % tenant_name)
        else:
            os_tenant = keystone.tenants.create(tenant_name="%s" % tenant_name,
                        description="VSD Managed Openstack Tenant",
                        enabled=True)
    except Exception, e:
        logger.error("|- ERROR creating tenant %s in keystone" % tenant_name)
        logger.error(repr(e))
    try:    
        admin_role = keystone.roles.find(name='admin')
    except Exception, e:
        logger.error("|- ERROR finding admin role in keystone")
        logger.error(repr(e))
    try:
        os_admin = keystone.users.find(name=cfg.get('openstack','admin_username'))
    except Exception, e:
        logger.error("|- ERROR finding user %s in keystone" % cfg.get('openstack','admin_username'))
        logger.error(repr(e))
    try:
        logger.info("Adding admin role for user %s in tenant %s in keystone" % (cfg.get('openstack','admin_username'),tenant_name))
        keystone.roles.add_user_role(os_admin, admin_role, os_tenant)
    except Exception, e:
        logger.error("|- ERROR adding admin role for user %s in tenant %s in keystone" % (cfg.get('openstack','admin_username'),tenant_name))
        logger.error(repr(e))
    neutron_creds = get_neutron_creds(cfg.get('openstack','admin_username'), cfg.get('openstack','admin_password'), "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        logger.info("Creating Net-Partition: %s" % tenant_name)
        body_netpart = {"net_partition":
                        {
                          "name": tenant_name,
                        }
                       }
        netpart = neutron.create_net_partition(body=body_netpart)
    except Exception, e:
        logger.error("|- ERROR creating netpartition: %s" % tenant_name)
        logger.error(repr(e))
    logger.info("Finished Creating VSD Managed Tenant: %s" % tenant_name)


def delete_vsd_managed_tenant(tenant_name,force):
    logger.info("Deleting VSD Managed Tenant: %s" % tenant_name)
    creds = get_keystone_creds()
    keystone = ksclient.Client(**creds)
    if force:
        try:
            delete_vms_in_tenant(tenant_name)
        except Exception, e:
            logger.error("|- ERROR deleting VMs from tenant %s" % tenant_name)
            logger.error(repr(e))
        try:
            delete_vsdobjects_in_tenant(tenant_name)
        except Exception, e:
            logger.error("|- ERROR deleting VSD Objects from tenant %s" % tenant_name)
            logger.error(repr(e))
    if keystone_tenant_exists(tenant_name):
        try:
            logger.info("Deleting Keystone Tenant: %s" % tenant_name)
            os_tenant = keystone.tenants.find(name="%s" % tenant_name)
            os_tenant.delete()
        except Exception, e:
            logger.error("|- ERROR deleting tenant %s in keystone" % tenant_name)
            logger.error(repr(e))
            return 1
    else:
        logger.info("Keystone tenant %s not present" % tenant_name)
    neutron_creds = get_neutron_creds(cfg.get('openstack','admin_username'), cfg.get('openstack','admin_password'), "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        logger.info("Deleting Net-Partition: %s" % tenant_name)
        if not netpartition_exists(tenant_name):
            logger.error("|- Netpartition: %s not found. Already deleted?" % tenant_name)
            return 
        netpart = neutron.list_net_partitions(name=tenant_name)['net_partitions'][0]
        neutron.delete_net_partition(netpart['id'])
    except Exception, e:
        logger.error("|- ERROR deleting netpartition: %s" % tenant_name)
        logger.error(repr(e))
    logger.info("Finished Deleting VSD Managed Tenant: %s" % tenant_name)

