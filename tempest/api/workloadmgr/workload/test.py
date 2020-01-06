import sys
import os
sys.path.append(os.getcwd())
from tempest.api.workloadmgr import base
from tempest import config
from oslo_log import log as logging
import time

LOG = logging.getLogger(__name__)
CONF = config.CONF

class WorkloadTest(base.BaseWorkloadmgrTest):

    credentials = ['primary']

    @classmethod
    def setup_clients(cls):
        super(WorkloadTest, cls).setup_clients()
        cls.client = cls.os.wlm_client

    def test_tvault1033_create_workload(self):
	try:
            self.vm_id = self.create_vm()
            LOG.debug("VM ID: " + str(self.vm_id))
            self.workload_create([self.vm_id],"2ddd528d-c9b4-4d7e-8722-cc395140255a")

        except Exception as e:
            LOG.error("Exception: " + str(e))