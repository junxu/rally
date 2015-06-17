# Copyright 2013: Mirantis Inc.
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

import jsonschema

from rally.deploy.serverprovider import provider
from rally.deploy.serverprovider.providers import existing
from tests.unit import test


class ExistingServersTestCase(test.TestCase):
    def setUp(self):
        super(ExistingServersTestCase, self).setUp()
        self.config = {"type": "ExistingServers",
                       "credentials": [{"user": "user", "host": "host1"},
                                       {"user": "user", "host": "host2"}]}

    def test_create_servers(self):
        _provider = provider.ProviderFactory.get_provider(self.config,
                                                          None)
        credentials = _provider.create_servers()
        self.assertEqual(["host1", "host2"], [s.host for s in credentials])
        self.assertEqual(["user", "user"], [s.user for s in credentials])

    def test_invalid_config(self):
        self.config["type"] = 42
        self.assertRaises(jsonschema.ValidationError,
                          existing.ExistingServers, None, self.config)

    def test_invalid_credentials(self):
        self.config["credentials"] = ["user@host1", "user@host2"]
        self.assertRaises(jsonschema.ValidationError,
                          existing.ExistingServers, None, self.config)
