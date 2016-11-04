# nuage-amp

The goal of `nuage-amp-sync` is to provide an automatic synchronization between Nuage Networks domain topologies and OpenStack tenant networks. As such, an end-user can easily provision new virtual machines in networks that have been created by the network admin.

Internally it monitors the creation and removal of subnets in Nuage enterprises and ensures the coresponding networks and subnets are mapped in OpenStack. It covers subnets of L3 domains and DHCP-Managed L2 domains. It does not support Shared Subnets, FloatingIP Subnets, or other types of L2 domains.

As an example, suppose a network administrator of the *ACME* enterprise has created the following topology in VSD Architect:
![Nuage-Enterprise-Topology][nuage-subnet-list]

These subnets will be made available to the *ACME* tenant in OpenStack like this:
![OpenStack-Network-List][os-subnet-list]

# Usage

The `nuage-amp-sync` synchronizes networks between a Nuage Networks Enterprise and an OpenStack Tenant.
For the example of Nuage Networks Enterprise `ACME`, it expects following OpenStack commands to be issued first:

```
# keystone tenant-create --name ACME
# keystone user-role-add --user admin --tenant ACME --role admin
# neutron nuage-netpartition-create ACME
```

This is sufficient for `nuage-amp-sync`  to start populating the ACME tenant with all networks as they are provisioned under the Nuage Networks ACME enterprise. It will use the admin user as configured in the `nuage-amp.conf` file.


# Install Instructions

The below instructions will install the nuage-amp tool on a RHEL or CentOS machine.

## Assumptions

- Nuage VSP is installed and configured in the network,
- The following OpenStack services are installed and configured,
 - Identity (Keystone),
 - Networking (Neutron),
 - Compute (Nova).
 - Nuage Neutron Plugin is installed and configured on the neutron server.

## Tested OpenStack Distributions

- Icehouse
 - Ubuntu Cloud Archive Icehouse with 12.04.5 or 14.04.1
 - Red Hat OSP 5.0 
- Juno
 - Ubuntu Cloud Archive 14.04.1
 - Red Hat RDO 6.0 / OSP 6.0
- Kilo
 - Red Hat RDO 7.0 / OSP 7.0
- Liberty
 - Red Hat RDO 7.0 / OSP 8.0

## Required Software Packages

The following software must be available on the linux server/VM:

- Python interpreter 2.7,
 - python-docopt,
 - MySQL-python,
- OpenStack: python-keystoneclient
- OpenStack: python-neutronclient


## Installation Steps for a CentOS / RedHat server

The procedure below explains the first time installation. Follow the steps in the Upgrade section when an older version of `nuage-amp` is already deployed.

Step 1: Login as a root to a server or a VM, and navigate to the directory where nuage-amp is to be installed

Step 2: Clone the `nuage-amp` software from github, and run the `setup.py install` script

```
# git clone https://github.com/nuagecommunity/nuage-amp.git
# cd nuage-amp
# python setup.py install
```

# Configuration

Step 1: Open the configuration file `/etc/nuage-amp/nuage-amp.conf` with a text editor.

```
# vi /etc/nuage-amp/nuage-amp.conf
```

Step 2: Set the server where nuage-amp resides.

```
[DEFAULT]
hostname = <nuage-amp host ip>
```

Step 3: Configure logging.

```
[logging]
loglevel = INFO
rotate_logfiles = True
maxsize = <maximum size of one logfile in Mega bytes>
backups = <maximum number of logfiles>
```

Step 4: Set the VSD server and configure a `csp` administrative user

```
[vsd]
hostname = <vsd host ip>
port = 8443
username = csproot 
password = csproot
enterprise = csp
version = v3_2
```

Step 5: set the OpenStack credentials.

- Use admin user and tenant, the admin user must have `admin` role for all projects to synchronize,
- Set `default_net_partition` to a value of `default_net_partition_name` in `/etc/neutron/plugins/nuage/nuage_plugin.ini`,
- Set `version` to the OpenStack version you would like to integrate to : [ icehouse | juno | kilo ]

```
[openstack]
admin_username = admin
admin_password = <admin password>
admin_tenant = admin
default_net_partition = <Openstack_Org>
auth_url = http:// <keystone host ip>:5000/v2.0/
version = juno

[neutron]
hostname = <neutron host ip>
db_hostname = <neutron mysql host ip>
db_username = <neutron mysql username>
db_password = <neutron mysql password>
db_name = <neutron DB name>
```

Step 6: Configure the format for subnet names under OpenStack
You can also specify a comma-separated list of tenants that should not be included for synchronizion. Typically you would include the name of the default Nuage enterprise used for OpenStack-Managed networking.

```
[sync]
l2_name_format = $d
l3_name_format = $d ($z) \ $s
excluded_tenants= Openstack_Org
sync_shared_subnets = False
```

By default, nuage-amp will not synchronize Nuage (L2/L3) Shared Subnets. This can be enabled by setting sync_shared_subnets to True. However, it's up to the end-user to avoid any IP conflicts. For example, if two tenants both use the same shared subnet and both create a VM in it, OpenStack could potentially pick the same IP address (not knowing they belong to the same Nuage subnet). To avoid conflicts, create a port with the fixed-ip option and attach it to the VM during creation.

```
neutron port-create <NETWORK> --fixed-ip ip_address=<IP_ADDR>
```

Another way of preventing IP conflicts in shared subnets is the use of allocation pools. Because the number and size of the pools differs for each use case, this functionality has not been built in. 

Step 7: Enable and start `nuage-amp-sync` through `systemctl`.

```
# systemctl daemon-reload
# systemctl start nuage-amp-sync
# systemctl enable nuage-amp-sync
# systemctl status nuage-amp-sync.service
Active: active (running)
```

[nuage-subnet-list]: sample/Nuage-subnet-list.PNG
[os-subnet-list]: sample/OS-subnet-list.PNG



