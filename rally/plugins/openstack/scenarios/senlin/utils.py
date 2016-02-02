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

import time

from oslo_config import cfg
import requests

from rally.common import logging
from rally.common import utils as rutils
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils
from senlinclient.common import utils as  senlin_utils

LOG = logging.getLogger(__name__)

SENLIN_BENCHMARK_OPTS = [
    cfg.FloatOpt("senlin_cluster_create_prepoll_delay",
                 default=2.0,
                 help="Time(in sec) to sleep after creating a resource before "
                      "polling for it status."),
    cfg.FloatOpt("senlin_cluster_create_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for senlin cluster to be created."),
    cfg.FloatOpt("senlin_cluster_create_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "cluster creation."),
    cfg.FloatOpt("senlin_cluster_delete_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for senlin cluster to be deleted."),
    cfg.FloatOpt("senlin_cluster_delete_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "cluster deletion."),
    cfg.FloatOpt("senlin_cluster_check_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for cluster to be checked."),
    cfg.FloatOpt("senlin_cluster_check_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "cluster checking."),
    cfg.FloatOpt("senlin_cluster_scale_timeout",
                 default=3600.0,
                 help="Time (in sec) to wait for cluster to scale up or down."),
    cfg.FloatOpt("senlin_cluster_scale_poll_interval",
                 default=1.0,
                 help="Time interval (in sec) between checks when waiting for "
                      "a cluster to scale up or down."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(SENLIN_BENCHMARK_OPTS, group=benchmark_group)


class SenlinScenario(scenario.OpenStackScenario):
    """Base class for Heat scenarios with basic atomic actions."""

    @atomic.action_timer("senlin.list_clusters")
    def _list_clusters(self):
        """Return user cluster list."""

        return list(self.clients("senlin").clusters())

    @atomic.action_timer("senlin.create_cluster")
    def _create_cluster(self, profile, min_size=0, max_size=-1,
                        desired_capacity=0, timeout=None):
        """Create a new cluster.

        :param profile: Profile Id used for this cluster.
        :param min_size: Min size of the cluster.
        :param desired_capacity: Desired capacity of the cluster.
        :param max_size: Max size of the cluster. 
        :param timeout: Cluster creation timeout in seconds.

        :returns: object of cluster
        """
        if not desired_capacity or desired_capacity < min_size:
            desired_capacity = min_size

        cluster_name = self.generate_random_name()
        kw = {
            "name": cluster_name,
            'profile_id': args.profile,
            "min_size": min_size,
            "desired_capacity": desired_capacity,
            "max_size": max_size,
            "timeout": timeout
        }

        cluster = self.clients("senlin").create_cluster(**kw)
        cluster_id = cluster["id"]

        time.sleep(CONF.benchmark.senlin_cluster_create_prepoll_delay)

        cluster = utils.wait_for(
            cluster,
            ready_statuses=["ACTIVE"],
            failure_statuses=["ERROR"],
            update_resource=self._update_cluster,
            timeout=CONF.benchmark.senlin_cluster_create_timeout,
            check_interval=CONF.benchmark.senlin_cluster_create_poll_interval)

        return cluster

    @atomic.action_timer("senlin.delete_cluster")
    def _delete_cluster(self, cluster):
        """Delete given cluster.

        Returns when the cluster is actually deleted.

        :param cluster: cluster object
        """
        LOG.debug("Deleting cluster `%s`" % cluster.id)
        self.clients("senlin").delete_cluster(cluster.id)
        #cluster.delete()
        utils.wait_for(
            cluster,
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.senlin_cluster_delete_timeout,
            check_interval=CONF.benchmark.senlin_cluster_delete_poll_interval,
            is_ready=self._is_cluster_deleted)

    def _is_cluster_deleted(self, cluster):
        LOG.debug("Checking cluster `%s` to be deleted. Status: `%s`" %
                  (cluster.name, cluster.status))
        try:
            self.clients("senlin").get_cluster(cluster.id)
            return False
        except Exception:
            return True
 
    @atomic.action_timer("senlin.scale_up")
    def _scale_cluster_up(self, cluster, count):
        """Remove a given number of worker nodes from the cluster.

        :param cluster: The cluster to be scaled
        :param count: The number of nodes to be added.
        """
        LOG.debug("Scale-out cluster `%s`" % cluster.id)
        self.clients("senlin").cluster_scale_out(cluster.id, count)
        self._wait_active(cluster)

    @atomic.action_timer("senlin.scale_down")
    def _scale_cluster_down(self, cluster, count):
        """Remove a given number of worker nodes from the cluster.

        :param cluster: The cluster to be scaled
        :param count: The number of nodes to be removed.
        """
        LOG.debug("Scale-in cluster `%s`" % cluster.id)
        self.clients("senlin").cluster_scale_in(cluster.id, count)
        self._wait_active(cluster)

    def _scale_cluster(self, cluster, delta):
        """Scale a given number of worker nodes from the cluster.

        :param cluster: The cluster to be scaled
        :param delta: The number of nodes to be scaled.
        """
        LOG.debug("Scale cluster `%s`" % cluster.id)
        if delta > 0 :
            self._scale_cluster_down(cluster, delta)
        else:
            self._scale_cluster_up(cluster, abs(delta))

    def _wait_active(self, cluster):
        utils.wait_for(
            resource=cluster, ready_statuses=["ACTIVE"],
            failure_statuses=["WARNING"], update_resource=self._update_cluster,
            timeout=CONF.benchmark.senlin_cluster_create_timeout,
            check_interval=CONF.benchmark.senlin_cluster_check_interval)
        
    def _update_cluster(self, cluster):
        return self.clients("senlin").get_cluster(cluster.id)

    def _create_profile(self, spec_file, profile_name):
        LOG.debug("Create profile.")
        spec =  senlin_utils.get_spec_content(spec_file)
        type_name = spec.get('type', None)
        type_version = spec.get('version', None)
        properties = spec.get('properties', None)

        params = {
            'name': profile_name,
            'spec': spec,
        }
     
        profile = self.clients("senlin").create_profile(**params)
        return profile

    def _delete_profile(self, profile):
        LOG.debug("Delete profile `%s`" % profile.id)
        service.delete_profile(profile.id)

def init_senlin_context(context_instance):
    context_instance.context["senlin"] = context_instance.context.get("senlin",
                                                                      {})
    for user, tenant_id in rutils.iterate_per_tenants(
            context_instance.context["users"]):
        context_instance.context["tenants"][tenant_id]["senlin"] = (
            context_instance.context["tenants"][tenant_id].get("senlin", {}))
