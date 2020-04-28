# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.
import logging
import asyncio
import binascii
import datetime

from passlib.apps import custom_app_context as pwd_context
from hbmqtt.plugins import schnorr


class BaseAuthPlugin:
    def __init__(self, context):
        self.context = context
        try:
            self.auth_config = self.context.config['auth']
        except KeyError:
            self.context.logger.warning("'auth' section not found in context configuration")

    def authenticate(self, *args, **kwargs):
        if not self.auth_config:
            # auth config section not found
            self.context.logger.warning("'auth' section not found in context configuration")
            return False
        return True


class AnonymousAuthPlugin(BaseAuthPlugin):
    def __init__(self, context):
        super().__init__(context)

    @asyncio.coroutine
    def authenticate(self, *args, **kwargs):
        authenticated = super().authenticate(*args, **kwargs)
        if authenticated:
            allow_anonymous = self.auth_config.get('allow-anonymous', True)  # allow anonymous by default
            if allow_anonymous:
                authenticated = True
                self.context.logger.debug("Authentication success: config allows anonymous")
            else:
                try:
                    session = kwargs.get('session', None)
                    authenticated = True if session.username else False
                    if self.context.logger.isEnabledFor(logging.DEBUG):
                        if authenticated:
                            self.context.logger.debug("Authentication success: session has a non empty username")
                        else:
                            self.context.logger.debug("Authentication failure: session has an empty username")
                except KeyError:
                    self.context.logger.warning("Session informations not available")
                    authenticated = False
        return authenticated


class FileAuthPlugin(BaseAuthPlugin):
    def __init__(self, context):
        super().__init__(context)
        self._puks = []  # to store allowed public keys
        self._users = dict()
        self._read_password_file()

    def _read_password_file(self):
        password_file = self.auth_config.get('password-file', None)
        if password_file:
            try:
                with open(password_file) as f:
                    self.context.logger.debug("Reading user database from %s" % password_file)
                    for l in f:
                        # line = l.strip()
                        if not l.startswith('#'):  # Allow comments in files
                            (username, pwd_hash_or_puk) = [
                                e.strip() for e in l.split(sep=":", maxsplit=3)
                            ]
                            if username:
                                # in passord file a public key is set like :
                                # secp256k1.puk:
                                if username == "secp256k1.puk":
                                    self._puks.append(pwd_hash_or_puk)
                                    self.context.logger.debug("secp256k1 public key %s added" % pwd_hash_or_puk)
                                else:
                                    self._users[username] = pwd_hash_or_puk
                                    self.context.logger.debug("user %s , hash=%s" % (username, pwd_hash_or_puk))
                self.context.logger.debug("%d user(s) read from file %s" % (len(self._users), password_file))
            except FileNotFoundError:
                self.context.logger.warning("Password file %s not found" % password_file)
        else:
            self.context.logger.debug("Configuration parameter 'password_file' not found")

    @asyncio.coroutine
    def authenticate(self, *args, **kwargs):
        authenticated = super().authenticate(*args, **kwargs)
        if authenticated:
            session = kwargs.get('session', None)
            if session.username:
                hash = self._users.get(session.username, None)
                if not hash:
                    authenticated = False
                    self.context.logger.debug("No hash found for user '%s'" % session.username)
                else:
                    authenticated = pwd_context.verify(session.password, hash)
            else:
                return None
        return authenticated


class Secp256k1AuthPlugin(FileAuthPlugin):
    """
    This plugin allows secure identification without ssl.
    """

    @asyncio.coroutine
    def authenticate(self, *args, **kwargs):
        authenticated = super().authenticate(*args, **kwargs)
        if authenticated:
            session = kwargs.get('session', None)
            if session.username:
                puk = session.username
                if puk not in self._puks:
                    authenticated = False
                    self.context.logger.debug("public key %s not found" % puk)
                else:
                    now = datetime.datetime.now()
                    iso_now = now.isoformat()[:16]
                    iso_now_m1 = (
                        now - datetime.timedelta(1.0 / 1440)
                    ).isoformat()[:16]

                    msg = schnorr.hash_sha256(iso_now + session.client_id)
                    msg_m1 = schnorr.hash_sha256(iso_now_m1 + session.client_id)

                    puk = binascii.unhexlify(puk[-64:])
                    sig = binascii.unhexlify(session.password)
                    authenticated = any([
                        schnorr.verify(msg, puk, sig),
                        schnorr.verify(msg_m1, puk, sig)
                    ])
            else:
                return None
        return authenticated
