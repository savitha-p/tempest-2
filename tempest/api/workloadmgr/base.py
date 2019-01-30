# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time
import json
import paramiko
import os
import stat
import requests
import re
import collections

from oslo_log import log as logging
from tempest import config
import tempest.test
from tempest.common import waiters
from oslo_config import cfg
from tempest_lib import exceptions as lib_exc
from datetime import datetime
from datetime import timedelta

CONF = config.CONF
LOG = logging.getLogger(__name__)

class BaseWorkloadmgrTest(tempest.test.BaseTestCase):

    _api_version = 2
    force_tenant_isolation = False
    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(BaseWorkloadmgrTest, cls).setup_clients()
        cls.subnets_client = cls.os.subnets_client
        cls.wlm_client = cls.os.wlm_client
        cls.servers_client = cls.os.servers_client
        cls.server_groups_client = cls.os.server_groups_client
        cls.flavors_client = cls.os.flavors_client
        cls.images_client = cls.os.image_client_v2
        cls.extensions_client = cls.os.extensions_client
        cls.floating_ip_pools_client = cls.os.floating_ip_pools_client
        cls.floating_ips_client = cls.os.floating_ips_client
        cls.keypairs_client = cls.os.keypairs_client
        cls.security_group_rules_client = cls.os.security_group_rules_client
        cls.security_groups_client = cls.os.security_groups_client
        cls.quotas_client = cls.os.quotas_client
        cls.quota_classes_client = cls.os.quota_classes_client
        cls.compute_networks_client = cls.os.compute_networks_client
        cls.limits_client = cls.os.limits_client
        cls.volumes_extensions_client = cls.os.volumes_extensions_client
        cls.snapshots_extensions_client = cls.os.snapshots_extensions_client
        cls.network_client = cls.os.networks_client
        cls.interfaces_client = cls.os.interfaces_client
        cls.fixed_ips_client = cls.os.fixed_ips_client
        cls.availability_zone_client = cls.os.availability_zone_client
        cls.agents_client = cls.os.agents_client
        cls.aggregates_client = cls.os.aggregates_client
        cls.services_client = cls.os.services_client
        cls.instance_usages_audit_log_client = (
            cls.os.instance_usages_audit_log_client)
        cls.hypervisor_client = cls.os.hypervisor_client
        cls.certificates_client = cls.os.certificates_client
        cls.migrations_client = cls.os.migrations_client
        cls.security_group_default_rules_client = (
            cls.os.security_group_default_rules_client)
        cls.versions_client = cls.os.compute_versions_client

	if CONF.volume_feature_enabled.api_v1:
            cls.volumes_client = cls.os.volumes_client
        else:
            cls.volumes_client = cls.os.volumes_v2_client
	    cls.volumes_client.service = 'volumev2'

	if CONF.identity_feature_enabled.api_v2:
	    cls.identity_client = cls.os.identity_client
	else:
	    cls.identity_client = cls.os.identity_v3_client


    @classmethod
    def register_custom_config_opts(cls):
        conf = cfg.CONF
        volume_opts = [
                   cfg.StrOpt('volume_type_nfs', default='123233'),
                   cfg.StrOpt('volume_type_ceph', default='31312323'),
                ]
        conf.register_opt(volume_opts, group='volume')

    @classmethod
    def resource_setup(cls):
        super(BaseWorkloadmgrTest, cls).resource_setup()

    @classmethod
    def resource_cleanup(cls):
        super(BaseWorkloadmgrTest, cls).resource_cleanup()

    '''
    Method returns the current status of a given workload
    '''
    def getWorkloadStatus(self, workload_id):
        resp, body = self.wlm_client.client.get("/workloads/"+workload_id)
        workload_status = body['workload']['status']
        LOG.debug("#### workloadid: %s , operation:show_workload" % workload_id)
        LOG.debug("Response:"+ str(resp.content))
        if(resp.status_code != 200):
            resp.raise_for_status()
        return workload_status

    '''
    Method returns the Instance ID of a new VM instance created
    '''
    def create_vm(self, vm_cleanup=True, vm_name="", security_group_id = "default", flavor_id =CONF.compute.flavor_ref, \
			key_pair = "", networkid=[{'uuid':CONF.network.internal_network_id}], image_id=CONF.compute.image_ref, block_mapping_data=[], a_zone=CONF.compute.vm_availability_zone):
	if(vm_name == ""):
	    ts = str(datetime.now())
	    vm_name = "Tempest_Test_Vm" + ts.replace('.','-')
        server=self.servers_client.create_server(name=vm_name,security_groups = [{"name":security_group_id}], imageRef=image_id, \
			flavorRef=flavor_id, networks=networkid,availability_zone=a_zone)
        server_id= server['server']['id']
        waiters.wait_for_server_status(self.servers_client, server_id, status='ACTIVE')
        return server_id


    '''
    Method creates a workload and returns Workload id
    '''
    def workload_create(self, instances, workload_type ,jobschedule={}, workload_name="", workload_cleanup=True, description='test'):
        if (1 == 0):
	    LOG.debug("True")
        else:
            in_list = []
            if(workload_name == ""):
		ts=str(datetime.now())
                workload_name = "tempest"+ ts.replace('.','-')
            for id in instances:
                in_list.append({'instance-id':id})
            payload={'workload': {'name': workload_name,
                              'workload_type_id': workload_type,
                              'source_platform': 'openstack',
                              'instances': in_list,
                              'jobschedule': jobschedule,
                              'metadata': {},
                              'description': description}}
            LOG.debug("Workload-create payload:: %s " % payload)
            resp, body = self.wlm_client.client.post("/workloads", json=payload)
            workload_id = body['workload']['id']
            LOG.debug("#### workloadid: %s , operation:workload_create" % workload_id)
            time.sleep(30)
            while (self.getWorkloadStatus(workload_id) != "available" and self.getWorkloadStatus(workload_id) != "error"):
                LOG.debug('workload status is: %s , sleeping for 30 sec' % self.getWorkloadStatus(workload_id))
                time.sleep(30)

            LOG.debug("Response:"+ str(resp.content))
            if(resp.status_code != 202):
                resp.raise_for_status()
        LOG.debug('WorkloadCreated: %s' % workload_id)
        return workload_id

    '''
    Method deletes a given workload
    '''
    def workload_delete(self, workload_id):
        try:
	    # Delete snapshot
            snapshot_list_of_workload = self.getSnapshotList(workload_id)

            if len(snapshot_list_of_workload)>0:
		for i in range(0,len(snapshot_list_of_workload)):
                    self.snapshot_delete(workload_id,snapshot_list_of_workload[i])

            resp, body = self.wlm_client.client.delete("/workloads/"+workload_id)
            LOG.debug("#### workloadid: %s , operation: workload_delete" % workload_id)
            LOG.debug("Response:"+ str(resp.content))
	    LOG.debug('WorkloadDeleted: %s' % workload_id)
	    return True
        except Exception as e:
            return False

    '''
    Method to wait until the workload is available
    '''
    def wait_for_workload_tobe_available(self, workload_id):
        status = "available"
        start_time = int(time.time())
        LOG.debug('Checking workload status')
        while ( status != self.getWorkloadStatus(workload_id)):
            if ( self.getWorkloadStatus(workload_id) == 'error'):
                LOG.debug('workload status is: %s , workload create failed' % self.getWorkloadStatus(workload_id))
                #raise Exception("Workload creation failed")
		return False
            LOG.debug('workload status is: %s , sleeping for 30 sec' % self.getWorkloadStatus(workload_id))
            time.sleep(30)
        LOG.debug('workload status of workload %s: %s' % (workload_id, self.getWorkloadStatus(workload_id)))
	return True

