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
    """Benchmark scenarios for Senlin clusters."""

    @validation.required_services(consts.Service.SENLIN)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_and_list_cluster(self, min_size=0, max_size=-1,
                                desired_capacity=None, timeout=None):
        """Create a cluster and then list all clusters.

        Measure the "senlin cluster-create" and "senlin cluster-list" commands
        performance.

        :param profile: Profile Id used for this cluster.
        :param min_size: Min size of the cluster.
        :param desired_capacity: Desired capacity of the cluster.
        :param max_size: Max size of the cluster. 
        :param timeout: Cluster creation timeout in seconds.

        """
        profile = self.context["tenant"]["senlin"]["profile"]
        self._create_cluster(profile, min_size, max_size, desired_capacity,
                             timeout)
        self._list_clusters()

    @validation.required_services(consts.Service.SENLIN)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_and_delete_cluster(self, min_size=0, max_size=-1,
                                  desired_capacity=None, timeout=None):
        """Create and then delete a cluster.

        Measure the "senlin cluster-create" and "senlin cluster-delete" commands
        performance.

        :param profile: Profile Id used for this cluster.
        :param min_size: Min size of the cluster.
        :param desired_capacity: Desired capacity of the cluster.
        :param max_size: Max size of the cluster. 
        :param timeout: Cluster creation timeout in seconds.
        """

        profile = self.context["tenant"]["senlin"]["profile"]
        cluster = self._create_cluster(profile, min_size, max_size,
                                       desired_capacity, timeout)
        self._delete_stack(cluster)

    @validation.required_services(consts.Service.SENLIN)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_cluster_and_scale(self, deltas, min_size=0, max_size=-1,
                                 desired_capacity=None, timeout=None):
        """Create an cluster and invoke a scale action.

        Measure the performance of scale action.

        :param profile: Profile Id used for this cluster.
        :param min_size: Min size of the cluster.
        :param desired_capacity: Desired capacity of the cluster.
        :param max_size: Max size of the cluster. 
        :param timeout: Cluster creation timeout in seconds.
        :param delta: the number of instances the stack is expected to
                      change by.
        """
        profile = self.context["tenant"]["senlin"]["profile"]
        cluster = self._create_cluster(profile, min_size, max_size,
                                       desired_capacity, timeout)
        for delta in deltas: 
            self._scale_cluster(cluster, delta)

        self._delete_stack(cluster)
