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
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

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
    cfg.FloatOpt("heat_stack_check_timeout",
                 default=3600.0,
                 help="Time(in sec) to wait for stack to be checked."),
    cfg.FloatOpt("heat_stack_check_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "stack checking."),
    cfg.FloatOpt("heat_stack_scale_timeout",
                 default=3600.0,
                 help="Time (in sec) to wait for stack to scale up or down."),
    cfg.FloatOpt("heat_stack_scale_poll_interval",
                 default=1.0,
                 help="Time interval (in sec) between checks when waiting for "
                      "a stack to scale up or down."),
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
    def _create_cluster(self, profile, min_size=0, max_size=-1
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
            update_resource=utils.get_from_manager(["CREATE_FAILED"]),
            timeout=CONF.benchmark.heat_stack_create_timeout,
            check_interval=CONF.benchmark.heat_stack_create_poll_interval)

        return cluster

    @atomic.action_timer("senlin.delete_cluster")
    def _delete_cluster(self, cluster):
        """Delete given cluster.

        Returns when the cluster is actually deleted.

        :param cluster: cluster object
        """
        cluster.delete()
        utils.wait_for_status(
            cluster,
            ready_statuses=["deleted"],
            check_deletion=True,
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.heat_stack_delete_timeout,
            check_interval=CONF.benchmark.heat_stack_delete_poll_interval)

    def _count_instances(self, stack):
        """Count instances in a Heat stack.

        :param stack: stack to count instances in.
        """
        return len([
            r for r in self.clients("heat").resources.list(stack.id,
                                                           nested_depth=1)
            if r.resource_type == "OS::Nova::Server"])

    def _scale_cluster(self, stack, output_key, delta):
        """Scale a stack up or down.

        Calls the webhook given in the output value identified by
        'output_key', and waits for the stack size to change by
        'delta'.

        :param stack: stack to scale up or down
        :param output_key: The name of the output to get the URL from
        :param delta: The expected change in number of instances in
                      the stack (signed int)
        """
        num_instances = self._count_instances(stack)
        expected_instances = num_instances + delta
        LOG.debug("Scaling stack %s from %s to %s instances with %s" %
                  (stack.id, num_instances, expected_instances, output_key))
        with atomic.ActionTimer(self, "heat.scale_with_%s" % output_key):
            self._stack_webhook(stack, output_key)
            utils.wait_for(
                stack,
                is_ready=lambda s: (
                    self._count_instances(s) == expected_instances),
                update_resource=utils.get_from_manager(
                    ["UPDATE_FAILED"]),
                timeout=CONF.benchmark.heat_stack_scale_timeout,
                check_interval=CONF.benchmark.heat_stack_scale_poll_interval)

    def _stack_webhook(self, stack, output_key):
        """POST to the URL given in the output value identified by output_key.

        This can be used to scale stacks up and down, for instance.

        :param stack: stack to call a webhook on
        :param output_key: The name of the output to get the URL from
        :raises InvalidConfigException: if the output key is not found
        """
        url = None
        for output in stack.outputs:
            if output["output_key"] == output_key:
                url = output["output_value"]
                break
        else:
            raise exceptions.InvalidConfigException(
                "No output key %(key)s found in stack %(id)s" %
                {"key": output_key, "id": stack.id})

        with atomic.ActionTimer(self, "heat.%s_webhook" % output_key):
            requests.post(url).raise_for_status()
