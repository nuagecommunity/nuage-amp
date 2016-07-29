#!/usr/bin/env python
# encoding: utf-8

"""
@author: Philippe Jeurissen
@copyright: Alcatel-Lucent 2015
"""

from nuage_amp.utils.nuage import NuageConnection, NuageHTTPError, NuageResponse
import keystoneclient.v2_0.client as ksclient
from neutronclient.v2_0 import client as neutronclient
from nuage_amp.utils.log import logger
from nuage_amp.utils.config import cfg
import MySQLdb as mdb

mask_dictionary = {
    "240.0.0.0": "/4",
    "248.0.0.0": "/5",
    "252.0.0.0": "/6",
    "254.0.0.0": "/7",
    "255.0.0.0": "/8",
    "255.128.0.0": "/9",
    "255.192.0.0": "/10",
    "255.224.0.0": "/11",
    "255.240.0.0": "/12",
    "255.248.0.0": "/13",
    "255.252.0.0": "/14",
    "255.254.0.0": "/15",
    "255.255.0.0": "/16",
    "255.255.128.0": "/17",
    "255.255.192.0": "/18",
    "255.255.224.0": "/19",
    "255.255.240.0": "/20",
    "255.255.248.0": "/21",
    "255.255.252.0": "/22",
    "255.255.254.0": "/23",
    "255.255.255.0": "/24",
    "255.255.255.128": "/25",
    "255.255.255.192": "/26",
    "255.255.255.224": "/27",
    "255.255.255.240": "/28",
    "255.255.255.248": "/29",
    "255.255.255.252": "/30"
}


def net_nm_sanitizer(net, nm):
    if net is not None:
        return net + mask_dictionary[nm]
    else:
        return "None"


def get_keystone_creds():
    return {'username': cfg.get('openstack', 'admin_username'), 'password': cfg.get('openstack', 'admin_password'),
            'auth_url': cfg.get('openstack', 'auth_url'), 'tenant_name': "admin"}


def get_neutron_creds(user, pw, tenant):
    return {'username': user, 'password': pw, 'auth_url': cfg.get('openstack', 'auth_url'), 'tenant_name': tenant}


def get_enterprise(nc, resource_name):
    enterprise = nc.get("enterprises", filtertext="name == \"{0}\"".format(resource_name)).obj()[0]
    return enterprise


def get_enterprise_by_id(nc, resource_id):
    enterprise = nc.get("enterprises/{0}".format(resource_id)).obj()[0]
    return enterprise


def get_sharednwresource_by_id(nc, resource_id):
    resource = nc.get("sharednetworkresources/{0}".format(resource_id)).obj()[0]
    return resource


def calcL2SubnetName(nc, l2domain):
    if not cfg.has_option('sync', 'l2_name_format'):
        L2NameFormat = "$d"
    else:
        L2NameFormat = cfg.get('sync', 'l2_name_format')

    name = l2domain['name']
    return name


def calcL3SubnetName(nc, vsd_subnet):
    if not cfg.has_option('sync', 'l3_name_format'):
        L3NameFormat = "$d ($z) \ $s"
    else:
        L3NameFormat = cfg.get('sync', 'l3_name_format')
    name = L3NameFormat
    name = name.replace('$s', vsd_subnet['name'])
    if '$d' in L3NameFormat:
        zone = nc.get("zones/{0}".format(vsd_subnet['parentID'])).obj()[0]
        domain = nc.get("domains/{0}".format(zone['parentID'])).obj()[0]
        name = name.replace('$d', domain['name'])
        if '$z' in L3NameFormat:
            name = name.replace('$z', zone['name'])
    elif '$z' in L3NameFormat:
        zone = nc.get("zones/{0}".format(vsd_subnet['parentID'])).obj()[0]
        name = name.replace('$z', zone['name'])
    return name


def neutron_add_subnet(nc, vsd_subnet, tenant):
    neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'), cfg.get('openstack', 'admin_password'),
                                      tenant.name)
    neutron = neutronclient.Client(**neutron_creds)
    if not vsd_subnet['parentType'] == "enterprise" and vsd_subnet['address'] is None and vsd_subnet[
            'associatedSharedNetworkResourceID'] is None:
        logger.debug(
            "|- Ignoring subnet: (ID:{0}). This is a public subnet without a pool assignment yet.".format(
                vsd_subnet['ID']))
        return None
    if vsd_subnet['parentType'] == "enterprise":
        net_name = calcL2SubnetName(nc, vsd_subnet)
    else:
        net_name = calcL3SubnetName(nc, vsd_subnet)
    try:
        logger.debug("Checking if openstack network {0} already exists".format(net_name))
        netw = neutron.list_networks(name=net_name)['networks']
    except Exception, e:
        logger.error("|- ERROR checking if openstack network {0} exists".format(net_name))
        logger.error(repr(e))
    else:
        body_nw = {
            "network":
                {
                    "name": net_name,
                    "admin_state_up": True
                }
        }
        try:
            netw = neutron.create_network(body=body_nw)
        except Exception, e:
            logger.error("|- ERROR creating network: (ID:{0})".format(vsd_subnet['ID']))
            logger.error(repr(e))
            return None
    if vsd_subnet['parentType'] == "enterprise" and not vsd_subnet['DHCPManaged']:
        body_subnet = {
            "subnets": [
                {
                    "name": calcL2SubnetName(nc, vsd_subnet),
                    "cidr": "9.0.0.0/8",
                    "ip_version": 4,
                    "gateway_ip": "9.9.9.1",
                    "network_id": netw['network']['id'],
                    "nuagenet": vsd_subnet['ID'],
                    "net_partition": tenant.name,
                    "enable_dhcp": False
                }
            ]
        }
    elif vsd_subnet['associatedSharedNetworkResourceID'] is not None:
        body_subnet = {
            "subnets": [
                {
                    "name": calcL3SubnetName(nc, vsd_subnet),
                    "cidr": "9.0.0.0/8",
                    "ip_version": 4,
                    "gateway_ip": "9.9.9.1",
                    "network_id": netw['network']['id'],
                    "nuagenet": vsd_subnet['ID'],
                    "net_partition": tenant.name,
                    "enable_dhcp": False
                }
            ]
        }
    elif vsd_subnet['parentType'] == "enterprise" and vsd_subnet['DHCPManaged']:
        body_subnet = {
            "subnets": [
                {
                    "name": calcL2SubnetName(nc, vsd_subnet),
                    "cidr": "{0}".format(net_nm_sanitizer(vsd_subnet['address'], vsd_subnet['netmask'])),
                    "ip_version": 4,
                    "gateway_ip": vsd_subnet['gateway'],
                    "network_id": netw['network']['id'],
                    "nuagenet": vsd_subnet['ID'],
                    "net_partition": tenant.name
                }
            ]
        }
    else:
        body_subnet = {
            "subnets": [
                {
                    "name": calcL3SubnetName(nc, vsd_subnet),
                    "cidr": "{0}".format(net_nm_sanitizer(vsd_subnet['address'], vsd_subnet['netmask'])),
                    "ip_version": 4,
                    "gateway_ip": vsd_subnet['gateway'],
                    "network_id": netw['network']['id'],
                    "nuagenet": vsd_subnet['ID'],
                    "net_partition": tenant.name
                }
            ]
        }
    try:
        sub = neutron.create_subnet(body=body_subnet)
    except Exception, e:
        logger.error("|- ERROR creating subnet: (ID:{0})".format(vsd_subnet['ID']))
        logger.error(repr(e))
        try:
            neutron.delete_network(netw['network']['id'])
        except Exception, e:
            logger.error("|- ERROR error removing network: (ID:{0})".format(vsd_subnet['ID']))
            logger.error(repr(e))
        return None
    return sub


def neutron_delete_subnet(os_subnet, neutron):
    neutron.delete_network(os_subnet['network_id'])


def get_all_netpartitions(neutron):
    return neutron.list_net_partitions()


def get_current_subnet_mappings():
    con = mdb.connect(cfg.get('neutron', 'db_hostname'), cfg.get('neutron', 'db_username'),
                      cfg.get('neutron', 'db_password'), cfg.get('neutron', 'db_name'))
    cur = con.cursor(mdb.cursors.DictCursor)
    if not cfg.has_option('openstack', 'version'):
        cur.execute("SELECT * FROM nuage_subnet_l2dom_mapping")
    else:
        if cfg.get('openstack', 'version').lower() == "icehouse":
            cur.execute("SELECT * FROM subnet_l2dom_mapping")
        else:
            # juno, kilo and liberty
            cur.execute("SELECT * FROM nuage_subnet_l2dom_mapping")
    rows = cur.fetchall()
    return rows


def get_all_tenants():
    keystone_creds = get_keystone_creds()
    keystone = ksclient.Client(**keystone_creds)
    tenants = keystone.tenants.list()
    return tenants


def get_tenant(tenant_name):
    keystone_creds = get_keystone_creds()
    keystone = ksclient.Client(**keystone_creds)
    tenant = keystone.tenants.find(name=tenant_name)
    return tenant


def get_tenant_with_id(tenant_id):
    keystone_creds = get_keystone_creds()
    keystone = ksclient.Client(**keystone_creds)
    tenant = keystone.tenants.find(id=tenant_id)
    return tenant


def vsd_subnet_mapped(vsd_subnet, mappings):
    for mapping in mappings:
        if mapping["nuage_subnet_id"] == vsd_subnet['ID']:
            return True
    return False


def check_adress_match(os_subnet, vsd_subnet):
    if vsd_subnet['address'] is None and vsd_subnet['netmask'] is None:
        return True
    if vsd_subnet['parentType'] == "enterprise" and not vsd_subnet['DHCPManaged']:
        return True

    if os_subnet['cidr'] == net_nm_sanitizer(vsd_subnet['address'], vsd_subnet['netmask']):
        return True
    return False


def check_name_match(nc, os_subnet, vsd_subnet):
    if vsd_subnet['parentType'] == "enterprise":
        new_name = calcL2SubnetName(nc, vsd_subnet)
    else:
        new_name = calcL3SubnetName(nc, vsd_subnet)
    if os_subnet['name'] == new_name:
        return True
    return False


def cleanup_os_networks():
    neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'), cfg.get('openstack', 'admin_password'),
                                      "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        networks = neutron.list_networks()['networks']
    except Exception, e:
        logger.error("|- ERROR getting current networks from Openstack")
        logger.error(repr(e))
        return 1
    for nw in networks:
        if not is_excluded_keystone_tenant_id(nw['tenant_id']) and not nw['subnets']:
            try:
                logger.info("Found Network(ID: {0}) without attached subnet, deleting".format(nw['id']))
                neutron.delete_network(nw['id'])
            except Exception, e:
                logger.error("|- ERROR deleting empty network with ID:{0} from Openstack".format(nw['id']))
                logger.error(repr(e))
                return 1


def vsd_subnet_exists(os_subnet, mapping):
    nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                         username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'),
                         version=cfg.get('vsd', 'version'), port=cfg.get('vsd', 'port'))
    logger.debug("Checking if Openstack network({0},{1}) exists in the VSD".format(os_subnet['id'], os_subnet['name']))
    try:
        vsd_subnet = nc.get("subnets/{0}".format(mapping["nuage_subnet_id"])).obj()[0]
    except Exception, e:
        try:
            vsd_subnet = nc.get("l2domains/{0}".format(mapping["nuage_subnet_id"])).obj()[0]
        except Exception, e:
            logger.info("|- Subnet ({0} - ID:{1}) not found in VSD --> Removing".format(os_subnet['name'], os_subnet['id']))
            vsd_subnet = []
    return vsd_subnet


def is_excluded_tenant_name(tenant_name):
    try:
        if not cfg.has_option('sync', 'excluded_tenants'):
            return False
        excluded_tenants = cfg.get('sync', 'excluded_tenants').split(',')
        if tenant_name in excluded_tenants:
            return True
        elif cfg.has_option('openstack', 'default_net_partition'):
            if cfg.get('openstack', 'default_net_partition') == tenant_name:
                return True
        else:
            return False
    except Exception, e:
        logger.error("|- ERROR getting list of excluded tenants from config file")
        logger.error(repr(e))


def is_excluded_keystone_tenant_id(tenant_id):
    try:
        if not cfg.has_option('sync', 'excluded_tenants'):
            return False
        excluded_tenants = cfg.get('sync', 'excluded_tenants').split(',')
        try:
            tenant = get_tenant_with_id(tenant_id)
            if tenant.name in excluded_tenants:
                return True
            elif cfg.has_option('openstack', 'default_net_partition'):
                if cfg.get('openstack', 'default_net_partition') == tenant.name:
                    return True
            else:
                return False
        except Exception, e:
            logger.error("|- ERROR getting keystone tenant with id: {0}".format(tenant_id))
            logger.error(repr(e))
    except Exception, e:
        logger.error("|- ERROR checking if tenant is excluded")
        logger.error(repr(e))


def is_excluded_netpartition_id(netpartition_id):
    neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'), cfg.get('openstack', 'admin_password'),
                                      "admin")
    neutron = neutronclient.Client(**neutron_creds)
    try:
        if not cfg.has_option('sync', 'excluded_tenants'):
            return False
        excluded_tenants = cfg.get('sync', 'excluded_tenants').split(',')
        try:
            tenant = neutron.list_net_partitions(id=netpartition_id)['net_partitions'][0]
        except Exception, e:
            logger.error("|- ERROR getting netpartition with id: {0}".format(netpartition_id))
            logger.error(repr(e))
        if tenant['name'] in excluded_tenants:
            return True
        elif cfg.has_option('openstack', 'default_net_partition'):
            if cfg.get('openstack', 'default_net_partition') == tenant['name']:
                return True
        else:
            return False
    except Exception, e:
        logger.error("|- ERROR checking if tenant is excluded")
        logger.error(repr(e))


def sync_subnets():
    try:
        logger.info("Starting Subnet Synchronizing")
        neutron_creds = get_neutron_creds(cfg.get('openstack', 'admin_username'),
                                          cfg.get('openstack', 'admin_password'), "admin")
        neutron = neutronclient.Client(**neutron_creds)
        nc = NuageConnection(cfg.get('vsd', 'hostname'), enterprise=cfg.get('vsd', 'enterprise'),
                             username=cfg.get('vsd', 'username'), password=cfg.get('vsd', 'password'),
                             version=cfg.get('vsd', 'version'), port=cfg.get('vsd', 'port'))
        try:
            subnet_mappings = get_current_subnet_mappings()
        except Exception, e:
            logger.error("|- ERROR getting current subnet mappings from OpenStack MYSQL database")
            logger.error(repr(e))
            return
        # First clean up existing Networks without attached subnets
        try:
            logger.info("Cleaning up Networks without subnets attached")
            cleanup_os_networks()
        except Exception, e:
            logger.error("|- ERROR cleaning up Networks without subnets attached")
            logger.error(repr(e))

        # First: Check if existing subnets are still in the VSD and remove them in OpenStack if not present in the VSD
        for mapping in subnet_mappings:
            if is_excluded_netpartition_id(mapping['net_partition_id']):
                logger.debug(
                    "|- Ignoring subnet: (ID:{0}) because it is in the default net partition or is in the list of excluded tenants".format(
                        mapping['subnet_id']))
                continue
            try:
                os_subnet = neutron.list_subnets(id=mapping['subnet_id'])['subnets'][0]
            except Exception, e:
                logger.error("|- Error: Subnet {0} found in subnet mapping but not in OpenStack.".format(
                    mapping['subnet_id']))
                logger.error(repr(e))
            try:
                logger.debug("Checking if subnet {0} exists".format(mapping['subnet_id']))
                vsd_subnet = vsd_subnet_exists(os_subnet, mapping)
            except Exception, e:
                logger.error("|- ERROR checking if subnet {0} exists".format(mapping['subnet_id']))
                logger.error(repr(e))
            delete = True
            if vsd_subnet:
                if vsd_subnet['ID'] == mapping["nuage_subnet_id"] and check_adress_match(os_subnet, vsd_subnet) and check_name_match(
                        nc, os_subnet, vsd_subnet):
                    delete = False
                else:
                    logger.info(
                        "OpenStack subnet(ID:{0}) properties do not match the corresponding VSD Subnet(ID:{1})".format(
                            os_subnet['id'], vsd_subnet['ID']))
                if not vsd_subnet['parentType'] == "enterprise" and vsd_subnet['address'] is None and vsd_subnet[
                        'associatedSharedNetworkResourceID'] is None:
                    delete = True
            if delete:
                try:
                    os_subnet = neutron.list_subnets(id=mapping['subnet_id'])['subnets'][0]
                    neutron_delete_subnet(os_subnet, neutron)
                    logger.info("|- Removed subnet: ({0} - ID:{1})".format(os_subnet['name'], os_subnet['id']))
                except Exception, e:
                    logger.error("|- ERROR removing subnet: (ID:{0})".format(mapping['subnet_id']))
                    logger.error(repr(e))

        # Second: List new subnets in the VSD and map them in OpenStack
        try:
            subnet_mappings = get_current_subnet_mappings()
        except Exception, e:
            logger.error("|- ERROR getting current subnet mappings from OpenStack MYSQL database")
            logger.error(repr(e))
            return
        try:
            netpartitions = get_all_netpartitions(neutron)
        except Exception, e:
            logger.error("|- ERROR getting all net-partitions")
            logger.error(repr(e))
            return
        subnet_mapped = False
        for netpart in netpartitions['net_partitions']:
            if is_excluded_tenant_name(netpart['name']):
                continue
            try:
                tenant = get_tenant(netpart['name'])
            except Exception, e:
                logger.error("|- ERROR looking up tenant {0} in keystone".format(netpart['name']))
                logger.error(repr(e))
                continue
            logger.info("Synchronizing subnets for {0}".format(tenant.name))
            enterprise = get_enterprise_by_id(nc, netpart['id'])
            domains = nc.get("enterprises/{0}/domains".format(enterprise["ID"])).obj()
            for domain in domains:
                subnets = nc.get("domains/{0}/subnets".format(domain["ID"])).obj()
                for subnet in subnets:
                    if not vsd_subnet_mapped(subnet, subnet_mappings):
                        # Add subnet to Neutron
                        try:
                            logger.info(
                                "|- Adding L3 subnet: ([{0}: {1}] {2}: {3} - ID:{4}) ".format(
                                    tenant.name,
                                    domain['name'],
                                    subnet['name'],
                                    net_nm_sanitizer(
                                        subnet['address'],
                                        subnet['netmask']),
                                    subnet['ID']))
                            neutron_add_subnet(nc, subnet, tenant)
                        except Exception, e:
                            logger.error(
                                "|- ERROR adding L3 subnet: ([{0}: {1}] {2}: {3} - ID:{4}) ".format(
                                    tenant.name, domain['name'],
                                    subnet['name'],
                                    net_nm_sanitizer(
                                        subnet['address'],
                                        subnet['netmask']),
                                    subnet['ID']))
                            logger.error(repr(e))

            l2domains = nc.get("enterprises/{0}/l2domains".format(enterprise["ID"])).obj()
            for l2domain in l2domains:
                if not vsd_subnet_mapped(l2domain, subnet_mappings):
                    # Add subnet to Neutron
                    try:
                        logger.info("|- Adding L2 subnet: ([{0}: {1}] {2}: {3} - ID:{4}) ".format(
                            tenant.name,
                            domain['name'],
                            l2domain['name'],
                            net_nm_sanitizer(
                                l2domain['address'],
                                l2domain['netmask']),
                            l2domain['ID']))
                        neutron_add_subnet(nc, l2domain, tenant)
                    except Exception, e:
                        logger.error(
                            "|- ERROR adding L2 subnet: ([{0}: {1}] {2}: {3} - ID:{4}) ".format(
                                tenant.name,
                                domain['name'],
                                l2domain['name'],
                                net_nm_sanitizer(
                                    l2domain['address'],
                                    l2domain['netmask']),
                                l2domain['ID']))
                        logger.error(repr(e))

        logger.info("Subnet Synchronization Completed")
    except Exception, e:
        logger.error("|- Unknown Error!!!")
        logger.error(repr(e))
        return
