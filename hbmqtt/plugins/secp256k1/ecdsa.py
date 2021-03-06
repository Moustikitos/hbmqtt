# -*- encoding:utf-8 -*-

from hbmqtt.plugins.secp256k1 import *


def sign(msg, secret0, k=None, canonical=True):
    """
    Generate signature according to ``ECDSA`` scheme.

    Args:
        msg (:class:`bytes`): sha256 message-hash
        secret0 (:class:`bytes`): private key
        k (:class:`int`): nonce (random nonce used if k=None)
        canonical (:class:`bool`): canonalize signature
    Returns:
        :class:`bytes`: DER signature
    """
    k = (rand_k() if not k else k) % n
    Q = G * k
    invk = pow(k, n-2, n)

    r = Q.x % n
    if r == 0:
        return None

    s = (invk * (int_from_bytes(msg) + int_from_bytes(secret0) * r)) % n
    if s == 0:
        return None
    if canonical and (s > (n//2)):
        s = n-s

    return der_from_sig(r, s)


def rfc6979_sign(msg, secret0, canonical=True):
    """
    Generate signature according to ``ECDSA`` scheme using a `RFC-6979 nonce <\
https://tools.ietf.org/html/rfc6979#section-3.2>`_

    Args:
        msg (:class:`bytes`): sha256 message-hash
        secret0 (:class:`bytes`): private key
        canonical (:class:`bool`): canonalize signature
    Returns:
        :class:`bytes`: DER signature
    """
    V = None
    for i in range(1, 10):
        k, V = rfc6979_k(msg, secret0, V)
        sig = sign(msg, secret0, k, canonical)
        if sig:
            return sig
    return None


def verify(msg, pubkey, sig):
    """
    Check signature according to ``ECDSA`` scheme.

    Args:
        msg (:class:`bytes`): sha256 message-hash
        pubkey (:class:`bytes`): encoded public key
        sig (:class:`bytes`): signature
    Returns:
        :class:`bool`: True if match
    """
    r, s = sig_from_der(sig)
    if r is None or r > n or s > n:
        return False

    h = int_from_bytes(msg)
    c = pow(s, n-2, n)

    u1G = G * ((h*c) % n)
    # u2Q = PublicKey.decode(pubkey) * ((r*c) % n)
    u2Q = point_mul(PublicKey.decode(pubkey), ((r*c) % n))
    GQ = u1G + u2Q

    return (GQ.x % n) == r
