# -*- coding: utf-8 -*-
#
# This file is part of fedmsg.
# Copyright (C) 2017 Red Hat, Inc.
#
# fedmsg is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# fedmsg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with fedmsg; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Authors:  Jeremy Cline <jcline@redhat.com>
"""Tests for the :mod:`fedmsg.consumers` module."""

import os
import unittest

from moksha.hub.zeromq.zeromq import ZMQMessage
import mock

from fedmsg import crypto
from fedmsg.consumers import FedmsgConsumer
from fedmsg.tests.crypto.test_x509 import SSLDIR


class DummyConsumer(FedmsgConsumer):
    """Set attributes necessary to instantiate a consumer."""
    config_key = 'dummy'
    validate_signatures = True


class FedmsgConsumerValidateTests(unittest.TestCase):
    """Tests for the :meth:`FedmsgConsumer.validate` method."""

    def setUp(self):
        self.config = {
            'dummy': True,
            'ssldir': SSLDIR,
            'certname': 'shell-app01.phx2.fedoraproject.org',
            'ca_cert_cache': os.path.join(SSLDIR, 'ca.crt'),
            'ca_cert_cache_expiry': 1497618475,  # Stop fedmsg overwriting my CA, See Issue 420

            'crl_location': "http://threebean.org/fedmsg-tests/crl.pem",
            'crl_cache': os.path.join(SSLDIR, 'crl.pem'),
            'crl_cache_expiry': 1497618475,
            'crypto_validate_backends': ['x509'],
        }
        self.hub = mock.Mock(config=self.config)
        self.consumer = DummyConsumer(self.hub)

    def test_topic_mismatch(self):
        """Assert a RuntimeWarning is raised for topic mismatches."""
        message = {'topic': 't1', 'body': {'topic': 't2'}}

        self.assertRaises(RuntimeWarning, self.consumer.validate, message)

    def test_valid_signature(self):
        """Assert the API accepts and validates dictionary messages."""
        message = {'topic': 't1', 'body': crypto.sign({'topic': 't1'}, **self.config)}

        self.consumer.validate(message)

    def test_invalid_signature(self):
        """Assert a RuntimeWarning is raised for topic mismatches."""
        message = {'topic': 't1', 'body': crypto.sign({'topic': 't1'}, **self.config)}
        message['body']['signature'] = 'thisisnotmysignature'

        self.assertRaises(RuntimeWarning, self.consumer.validate, message)

    def test_no_topic_in_body(self):
        """Assert an empty topic is placed in the message if the key is missing."""
        self.consumer.validate_signatures = False
        message = {'body': {'some': 'stuff'}}

        self.consumer.validate(message)
        self.assertEqual({'body': {'topic': None, 'msg': {'some': 'stuff'}}}, message)

    @mock.patch('fedmsg.consumers.fedmsg.crypto.validate')
    def test_zmqmessage_text_body(self, mock_crypto_validate):
        self.consumer.validate_signatures = True
        self.consumer.hub.config = {}
        message = ZMQMessage(u't1', u'{"some": "stuff"}')

        self.consumer.validate(message)
        mock_crypto_validate.assert_called_once_with({'topic': u't1', 'msg': {'some': 'stuff'}})

    @mock.patch('fedmsg.consumers.warnings.warn')
    @mock.patch('fedmsg.consumers.fedmsg.crypto.validate')
    def test_zmqmessage_binary_body(self, mock_crypto_validate, mock_warn):
        self.consumer.validate_signatures = True
        self.consumer.hub.config = {}
        message = ZMQMessage(u't1', b'{"some": "stuff"}')

        self.consumer.validate(message)
        mock_crypto_validate.assert_called_once_with({'topic': u't1', 'msg': {'some': 'stuff'}})
        mock_warn.assert_any_call('Message body is not unicode', DeprecationWarning)