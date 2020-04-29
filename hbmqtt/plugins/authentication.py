# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.
import logging
import asyncio
import binascii
import datetime
import traceback

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
                        if not l.startswith('#'):  # Allow comments in files
                            (username, pwd_hash_or_puk) = [
                                e.strip() for e in l.split(sep=":", maxsplit=3)[:2]
                            ]  # so ' username : password ' gives same result than 'username:password'
                            if username:
                                # in passord file a public key is set like :
                                # secp256k1.puk:030cfbf62534dfa5f32e37145b27d2875c1a1ecf884e39f0b098e962acc7aeaaa7
                                if username == "secp256k1.puk":
                                    self._puks.append(pwd_hash_or_puk)
                                    self.context.logger.debug("secp256k1 public key %s added" % pwd_hash_or_puk)
                                else:
                                    self._users[username] = pwd_hash_or_puk
                                    self.context.logger.debug("user %s , hash=%s" % (username, pwd_hash_or_puk))
                self.context.logger.debug("%d user(s) read from file %s" % (len(self._users), password_file))
                self.context.logger.debug("%d secp256k1 public key granted from file %s" % (len(self._puks), password_file))
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
            allow_anonymous = self.auth_config.get('allow-anonymous', True)
            session = kwargs.get('session', None)
            if session.username:
                puk = session.username
                if not allow_anonymous and puk not in self._puks:
                    # public key is not registered
                    authenticated = False
                    self.context.logger.debug("public key %s not found" % puk)
                else:
                    # time is used to change signature identification every
                    # minutes. Test is performed on the curent utc minute and
                    # the one before. Isoformat is YYYY-MM-DDTHH:MM:SS.ffffff
                    # so isoformat() --> YYYY-MM-DDTHH:MM
                    now = datetime.datetime.utcnow()
                    iso_now = now.isoformat()[:16]
                    iso_now_m1 = (
                        now - datetime.timedelta(1.0 / 1440)  # 1440 = 24*60
                    ).isoformat()[:16]
                    # schnorr signature is issued on :
                    # isoformat(utcnow)[:16] + client id
                    msg = schnorr.hash_sha256(iso_now + session.client_id)
                    msg_m1 = schnorr.hash_sha256(
                        iso_now_m1 + session.client_id
                    )
                    # Schnorr protocol only uses x value of a secp256k1 point.
                    # puk[-64:] gives hexlified x value from encoded secp256k1
                    # point
                    try:
                        puk = binascii.unhexlify(puk[-64:])
                        sig = binascii.unhexlify(session.password)
                        authenticated = any([
                            schnorr.verify(msg, puk, sig),
                            schnorr.verify(msg_m1, puk, sig)
                        ])
                    except Exception as error:
                        self.context.logger.error(
                            "%r\n%s", error, traceback.format_exc()
                        )
                        self.context.logger.debug(
                            "secp256k1 auth error %s", session
                        )
                        return None
            else:
                return None
        return authenticated
