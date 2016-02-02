# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from rally.common.i18n import _
from rally.common import logging
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.context.cleanup import manager as resource_manager
from rally.plugins.openstack.scenarios.senlin import utils as senlin_utils
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="senlin_profile", order=440)
class SenlinProfile(context.Context):
    """Context class for create senlin profile."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "spec_file": {
                "type": "string"
            },
            "profile_name": {
                "type": "string",
            }
        },
        "oneOf": [
            {"required": ["spec_file"]}
        ],
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Senlin Profile`"))
    def setup(self):
        senlin_utils.init_senlin_context(self)

        spec_file = self.config.get("spec_file")
        profile_name = self.config.get("profile_name") 
        if not profile_name: 
            profile_name = self.generate_random_name()

        for user, tenant_id in rutils.iterate_per_tenants(
                self.context["users"]):
            senlin_scenario = senlin_utils.SenlinScenario(
                {"user": user, "task": self.context["task"]})
     
            profile = senlin_scenario._create_profile(
                spec_file, profile_name)

            self.context["tenants"][tenant_id]["senlin"]["profile"] = (
                profile.id)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Senlin Profile`"))
    def cleanup(self):
        resource_manager.cleanup(names=["senlin.profiles"],
                                 users=self.context.get("users", []))
