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
from rally.plugins.openstack.scenarios.senlin import utils
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
            {"required": ["spec_file", "profile_name"]}
        ],
        "additionalProperties": False
    }

    def _create_profile(self, spec_file, profile_name):
        scenario = glance_utils.GlanceScenario(
            {"user": user, "task": self.context["task"]})
        if not profile_name: 
            profile_name = self.generate_random_name()
        profile = scenario._create_profile(spec_file, profile_name)
        return profile.id

    @logging.log_task_wrapper(LOG.info, _("Enter context: `Senlin Profile`"))
    def setup(self):
        utils.init_sahara_context(self)
        self.context["senlin"]["profile"] = {}

        # The user may want to use the existing image. In this case he should
        # make sure that the image is public and has all required metadata.
        spec_file = self.config.get("spec_file")

        self.context["sahara"][""] = not image_uuid

        if image_uuid:
            # Using the first user to check the existing image.
            user = self.context["users"][0]
            clients = osclients.Clients(user["credential"])

            image = clients.glance().images.get(image_uuid)

            if not image.is_public:
                raise exceptions.BenchmarkSetupFailure(
                    "Image provided in the Sahara context should be public.")
            image_id = image_uuid

            for user, tenant_id in rutils.iterate_per_tenants(
                    self.context["users"]):
                self.context["tenants"][tenant_id]["sahara"]["image"] = (
                    image_id)
        else:
            for user, tenant_id in rutils.iterate_per_tenants(
                    self.context["users"]):

                image_id = self._create_image(
                    hadoop_version=self.config["hadoop_version"],
                    image_url=self.config["image_url"],
                    plugin_name=self.config["plugin_name"],
                    user=user,
                    user_name=self.config["username"])

                self.context["tenants"][tenant_id]["sahara"]["image"] = (
                    image_id)

    @logging.log_task_wrapper(LOG.info, _("Exit context: `Senlin Profile`"))
    def cleanup(self):

        # TODO(boris-42): Delete only resources created by this context
        if self.context["senlin"]["need_profile_cleanup"]:
            resource_manager.cleanup(names=["senlin.profiles"],
                                     users=self.context.get("users", []))
