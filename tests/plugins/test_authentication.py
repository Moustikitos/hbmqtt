# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.

import unittest
import logging
import os
import asyncio
import datetime
import binascii
from hbmqtt.plugins import schnorr
from hbmqtt.plugins.manager import BaseContext
from hbmqtt.plugins.authentication import AnonymousAuthPlugin, FileAuthPlugin, Secp256k1AuthPlugin
from hbmqtt.session import Session

formatter = "[%(asctime)s] %(name)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=formatter)


class TestAnonymousAuthPlugin(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def test_allow_anonymous(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'allow-anonymous': True
            }
        }
        s = Session()
        s.username = ""
        auth_plugin = AnonymousAuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertTrue(ret)

    def test_disallow_anonymous(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'allow-anonymous': False
            }
        }
        s = Session()
        s.username = ""
        auth_plugin = AnonymousAuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertFalse(ret)

    def test_allow_nonanonymous(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'allow-anonymous': False
            }
        }
        s = Session()
        s.username = "test"
        auth_plugin = AnonymousAuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertTrue(ret)


class TestFileAuthPlugin(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def test_allow(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd")
            }
        }
        s = Session()
        s.username = "user"
        s.password = "test"
        auth_plugin = FileAuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertTrue(ret)

    def test_wrong_password(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd")
            }
        }
        s = Session()
        s.username = "user"
        s.password = "wrong password"
        auth_plugin = FileAuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertFalse(ret)

    def test_unknown_password(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd")
            }
        }
        s = Session()
        s.username = "some user"
        s.password = "some password"
        auth_plugin = FileAuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertFalse(ret)


class TestSecp256k1AuthPlugin(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def test_good_anonymous(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd"),
                'allow-anonymous': True
            }
        }
        s = Session()
        s.client_id = "client_using_secp256k1"
        # secp256k1 public key from int(hashlib.sha256(b"other secret").digets())
        # puk = '02d3a9b4022ab24b9218ae3290d2cbecf6d773ef70769afe9f15e7055a79cc90c4'
        # prk = 'fffc49122308b5e5666e6874ff4535d5a0e3f270a3a7545703c59da25378cbb3'
        s.username = "02d3a9b4022ab24b9218ae3290d2cbecf6d773ef70769afe9f15e7055a79cc90c4"
        prk = binascii.unhexlify("fffc49122308b5e5666e6874ff4535d5a0e3f270a3a7545703c59da25378cbb3")
        msg = schnorr.hash_sha256(datetime.datetime.utcnow().isoformat()[:16] + s.client_id)
        s.password = binascii.hexlify(schnorr.sign(msg, prk))

        auth_plugin = Secp256k1AuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertTrue(ret)

    def test_bad_anonymous(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd"),
                'allow-anonymous': True
            }
        }
        s = Session()
        s.client_id = "client_using_secp256k1"
        # secp256k1 public key from int(hashlib.sha256(b"other secret").digets())
        # puk = '02d3a9b4022ab24b9218ae3290d2cbecf6d773ef70769afe9f15e7055a79cc90c4'
        # prk = 'fffc49122308b5e5666e6874ff4535d5a0e3f270a3a7545703c59da25378cbb3'
        s.username = "02d3a9b4022ab24b9218ae3290d2cbecf6d773ef70769afe9f15e7055a79cc90c4"
        prk = binascii.unhexlify("fffc49122308b5e5666e6874ff4535d5a0e3f270a3a7545703c59da25378cbb3")
        msg = schnorr.hash_sha256(datetime.datetime.utcnow().isoformat()[:16] + s.client_id[1:])  # remove first char of client_id to generate a bad signature
        s.password = binascii.hexlify(schnorr.sign(msg, prk))

        auth_plugin = Secp256k1AuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertFalse(ret)

    def test_bad_public_key(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd"),
                'allow-anonymous': False
            }
        }
        s = Session()
        s.client_id = "client_using_secp256k1"
        # secp256k1 public key from int(hashlib.sha256(b"other secret").digets())
        # puk = '02d3a9b4022ab24b9218ae3290d2cbecf6d773ef70769afe9f15e7055a79cc90c4'
        # prk = 'fffc49122308b5e5666e6874ff4535d5a0e3f270a3a7545703c59da25378cbb3'
        s.username = "02d3a9b4022ab24b9218ae3290d2cbecf6d773ef70769afe9f15e7055a79cc90c4"
        prk = binascii.unhexlify("fffc49122308b5e5666e6874ff4535d5a0e3f270a3a7545703c59da25378cbb3")
        msg = schnorr.hash_sha256(datetime.datetime.utcnow().isoformat()[:16] + s.client_id)
        s.password = binascii.hexlify(schnorr.sign(msg, prk))

        auth_plugin = Secp256k1AuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertFalse(ret)

    def test_bad_signature(self):
        context = BaseContext()
        context.logger = logging.getLogger(__name__)
        context.config = {
            'auth': {
                'password-file': os.path.join(os.path.dirname(os.path.realpath(__file__)), "passwd"),
                'allow-anonymous': False
            }
        }
        s = Session()
        s.client_id = "client_using_secp256k1"
        # secp256k1 public key from int(hashlib.sha256(b"secret").digets())
        # puk = '030cfbf62534dfa5f32e37145b27d2875c1a1ecf884e39f0b098e962acc7aeaaa7'
        # prk = '2c495f4933631f014d93f059c15b03bac6eaaead53a675e09574c4bcccab09d6'
        s.username = "030cfbf62534dfa5f32e37145b27d2875c1a1ecf884e39f0b098e962acc7aeaaa7"  # the puk actually
        prk = binascii.unhexlify("2c495f4933631f014d93f059c15b03bac6eaaead53a675e09574c4bcccab09d6")
        msg = schnorr.hash_sha256(datetime.datetime.utcnow().isoformat()[:16] + s.client_id[1:])  # remove first char of client_id to generate a bad signature
        s.password = binascii.hexlify(schnorr.sign(msg, prk))

        auth_plugin = Secp256k1AuthPlugin(context)
        ret = self.loop.run_until_complete(auth_plugin.authenticate(session=s))
        self.assertFalse(ret)
