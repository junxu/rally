# Copyright 2015: Mirantis Inc.
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

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.senlin import utils as senlin_utils
from rally.task import context

LOG = logging.getLogger(__name__)


@context.configure(name="senlin_cluster", order=435)
class ClusterGenerator(context.Context):
    """Context class for create temporary clusters with resources.

       Cluster generator allows to generate arbitrary number of stacks for
       each tenant before test scenarios. In addition, it allows to define
       number of resources (namely OS::Heat::RandomString) that will be created
       inside each stack. After test execution the stacks will be
       automatically removed from heat.
    """

    # The schema of the context configuration format
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,

        "properties": {
            "clusters_per_tenant": {
                "type": "integer",
                "minimum": 1
            }
        },
        "additionalProperties": False
    }

    DEFAULT_CONFIG = {
        "clusters_per_tenant": 1
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Senlin Clusters`"))
    def setup(self):
        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            senlin_scenario = senlin_utils.SenlinScenario(
                {"user": user, "task": self.context["task"]})
            self.context["tenants"][tenant_id]["clusters"] = []
            for i in range(self.config["clusters_per_tenant"]):
                cluster = senlin_scenario._create_cluster()
                self.context["tenants"][tenant_id]["clusters"].append(cluster.id)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Senlin Clusters`"))
    def cleanup(self):
        resource_manager.cleanup(names=["senlin.clusters"],
                                 users=self.context.get("users", []))