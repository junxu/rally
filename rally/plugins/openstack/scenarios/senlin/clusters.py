# Copyright 2014: Mirantis Inc.
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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.senlin import utils
from rally.task import atomic
from rally.task import types
from rally.task import validation


class SenlinClusters(utils.SenlinScenario):
    """Benchmark scenarios for Heat stacks."""

    @types.set(template_path=types.FileType, files=types.FileTypeDict)
    @validation.required_services(consts.Service.SENLIN)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_and_list_cluster(self, template_path, parameters=None,
                              files=None, environment=None):
        """Create a cluster and then list all clusters.

        Measure the "senlin cluster-create" and "senlin cluster-list" commands
        performance.

        :param template_path: path to stack template file
        :param parameters: parameters to use in heat template
        :param files: files used in template
        :param environment: stack environment definition
        """
        self._create_cluster(template_path, parameters, files, environment)
        self._list_clusters()

    @types.set(template_path=types.FileType, files=types.FileTypeDict)
    @validation.required_services(consts.Service.SENLIN)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_and_delete_cluster(self, template_path, parameters=None,
                                  files=None, environment=None):
        """Create and then delete a cluster.

        Measure the "senlin cluster-create" and "senlin cluster-delete" commands
        performance.

        :param template_path: path to stack template file
        :param parameters: parameters to use in heat template
        :param files: files used in template
        :param environment: stack environment definition
        """

        stack = self._create_stack(template_path, parameters,
                                   files, environment)
        self._delete_stack(stack)

    @types.set(template_path=types.FileType, files=types.FileTypeDict)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_check_delete_cluster(self, template_path, parameters=None,
                                    files=None, environment=None):
        """Create, check and delete a stack.

        Measure the performance of the following commands:
        - heat stack-create
        - heat action-check
        - heat stack-delete

        :param template_path: path to stack template file
        :param parameters: parameters to use in heat template
        :param files: files used in template
        :param environment: stack environment definition
        """

        stack = self._create_stack(template_path, parameters,
                                   files, environment)
        self._check_stack(stack)
        self._delete_stack(stack)

    @types.set(template_path=types.FileType, files=types.FileTypeDict)
    @validation.required_services(consts.Service.HEAT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_cluster_and_scale(self, template_path, output_key, delta,
                                 parameters=None, files=None,
                                 environment=None):
        """Create an autoscaling stack and invoke a scaling policy.

        Measure the performance of autoscaling webhooks.

        :param template_path: path to template file that includes an
                              OS::Heat::AutoScalingGroup resource
        :param output_key: the stack output key that corresponds to
                           the scaling webhook
        :param delta: the number of instances the stack is expected to
                      change by.
        :param parameters: parameters to use in heat template
        :param files: files used in template (dict of file name to
                      file path)
        :param environment: stack environment definition (dict)
        """
        # * Kilo Heat can supply alarm_url attributes without needing
        #   an output key, so instead of getting the output key from
        #   the user, just get the name of the ScalingPolicy to apply.
        # * Kilo Heat changes the status of a stack while scaling it,
        #   so _scale_stack() can check for the stack to have changed
        #   size and for it to be in UPDATE_COMPLETE state, so the
        #   user no longer needs to specify the expected delta.
        stack = self._create_stack(template_path, parameters, files,
                                   environment)
        self._scale_stack(stack, output_key, delta)
