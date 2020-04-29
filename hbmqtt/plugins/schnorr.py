import hashlib
import future
from builtins import int, bytes, pow


p = int(0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f)
n = int(0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141)


def jacobi(x):
    return pow(x, (p - 1) // 2, p)


def is_quad(x):
    return jacobi(x) == 1


def hash_sha256(b):
    """
    Args:
        b (:class:`bytes` or :class:`str`): sequence to be hashed
    Returns:
        :class:`bytes`: sha256 hash
    """
    return hashlib.sha256(
        b if isinstance(b, bytes) else b.encode("utf-8")
    ).digest()


# precomputed hashtag
HASHED_TAGS = {
    "BIPSchnorrDerive": hash_sha256("BIPSchnorrDerive"),
    "BIPSchnorr": hash_sha256("BIPSchnorr"),
}


def tagged_hash(tag, msg):
    """
    Return ``sha256(sha256(tag) || sha256(tag) || msg)``. Tagged hash
    are registered to speed up code execution.

    Args:
        tag (:class:`str`): tag to use
        msg (:class:`bytes`): sha256 hash of message to sign
    Returns:
        :class:`bytes`: tagged hash
    """
    tag_hash = HASHED_TAGS.get(tag, False)
    if not tag_hash:
        tag_hash = hash_sha256(tag)
        HASHED_TAGS[tag] = tag_hash
    return hash_sha256(tag_hash + tag_hash + msg)


def x(P):
    """
    Return :class:`P.x` or :class:`P[0]`.

    Args:
        P (:class:`list`): ``secp256k1`` point
    Returns:
        :class:`int`: x
    """
    return P[0]


def y(P):
    """
    Return :class:`P.y` or :class:`P[1]`.

    Args:
        P (:class:`list`): ``secp256k1`` point
    Returns:
        :class:`int`: y
    """
    return P[1]


def point_add(P1, P2):
    """
    Add ``secp256k1`` points.

    Args:
        P1 (:class:`list`): first ``secp256k1`` point
        P2 (:class:`list`): second ``secp256k1`` point
    Returns:
        :class:`list`: ``secp256k1`` point
    """
    if (P1 is None):
        return P2
    if (P2 is None):
        return P1
    if (x(P1) == x(P2) and y(P1) != y(P2)):
        raise ValueError("One of the point is not on the curve")
    if (P1 == P2):
        lam = (3 * x(P1) * x(P1) * pow(2 * y(P1), p - 2, p)) % p
    else:
        lam = ((y(P2) - y(P1)) * pow(x(P2) - x(P1), p - 2, p)) % p
    x3 = (lam * lam - x(P1) - x(P2)) % p
    return [x3, (lam * (x(P1) - x3) - y(P1)) % p]


def point_mul(P, n):
    """
    Multiply ``secp256k1`` point with scalar.

    Args:
        P (:class:`list`): ``secp256k1`` point
        n (:class:`int`): scalar
    Returns:
        :class:`list`: ``secp256k1`` point
    """
    R = None
    for i in range(256):
        if ((n >> i) & 1):
            R = point_add(R, P)
        P = point_add(P, P)
    return R


def y_from_x(x):
    """
    Compute :class:`P.y` from :class:`P.x` according to ``y²=x³+7``.
    """
    y_sq = (pow(x, 3, p) + 7) % p
    y = pow(y_sq, (p + 1) // 4, p)
    if pow(y, 2, p) != y_sq:
        return None
    return y


def point_from_bytes(pubkeyB):
    """
    Decode a public key as defined in `BIP schnorr <https://github.com/sipa/bi\
ps/blob/bip-schnorr/bip-schnorr.mediawiki>`_ spec.

    Args:
        pubkeyB (:class:`bytes`): encoded public key
    Returns:
        :class:`Point`: secp256k1 curve point
    """
    x = int.from_bytes(pubkeyB, byteorder="big")
    y = y_from_x(x)
    if not y:
        return None
    return [x, y]


def bytes_from_int(x):
    return int(x).to_bytes(32, byteorder="big")


# Note that bip schnorr uses a very different public key format (32 bytes) than
# the ones used by existing systems (which typically use elliptic curve points
# as public keys, 33-byte or 65-byte encodings of them). A side effect is that
# ``PubKey(sk) = PubKey(bytes(n-int(sk))``, so every public key has two
# corresponding private keys.


def bytes_from_point(P):
    """
    Encode a public key as defined in `BIP schnorr <https://github.com/sipa/bi\
ps/blob/bip-schnorr/bip-schnorr.mediawiki>`_ spec.

    Args:
        P (:class:`Point`): secp256k1 curve point
    Returns:
        :class:`bytes`: encoded public key
    """
    return bytes_from_int(x(P))


def encoded_from_point(P):
    """
    Encode and compress a ``secp256k1`` point:
      * ``bytes(2) || bytes(x)`` if y is even
      * ``bytes(3) || bytes(x)`` if y is odd

    Args:
        P (:class:`list`): ``secp256k1`` point
    Returns:
        :class:`bytes`: compressed and encoded point
    """
    return (b"\x03" if y(P) & 1 else b"\x02") + bytes_from_int(x(P))


def sign(msg, seckey0):
    """
    Generate message signature according to `BIP schnorr <https://github.com/s\
ipa/bips/blob/bip-schnorr/bip-schnorr.mediawiki>`_ spec.

    Args:
        msg (:class:`bytes`): sha256 message-hash
        seckey0 (:class:`bytes`): private key
    Returns:
        :class:`bytes`: RAW signature
    """
    if len(msg) != 32:
        raise ValueError('The message must be a 32-byte array.')

    seckey0 = int.from_bytes(seckey0, byteorder="big")
    if not (1 <= seckey0 <= n - 1):
        raise ValueError(
            'The secret key must be an integer in the range 1..n-1.'
        )

    P = G * seckey0
    seckey = seckey0 if is_quad(P.y) else n - seckey0

    k0 = int.from_bytes(
        tagged_hash("BIPSchnorrDerive", bytes_from_int(seckey) + msg),
        byteorder="big"
    ) % n
    if k0 == 0:
        raise RuntimeError(
            'Failure. This happens only with negligible probability.'
        )

    R = G * k0
    k = n - k0 if not is_quad(R.y) else k0
    r = bytes_from_point(R)
    e = int.from_bytes(
        tagged_hash("BIPSchnorr", r + bytes_from_point(P) + msg),
        byteorder="big"
    ) % n

    return r + bytes_from_int((k + e * seckey) % n)


def verify(msg, pubkey, sig):
    """
    Check if public key match message signature according to `BIP schnorr <htt\
ps://github.com/sipa/bips/blob/bip-schnorr/bip-schnorr.mediawiki>`_ spec.

    Args:
        msg (:class:`bytes`): sha256 message-hash
        pubkey (:class:`bytes`): encoded public key
        sig (:class:`bytes`): signature
    Returns:
        :class:`bool`: True if match
    """
    if len(msg) != 32:
        raise ValueError('The message must be a 32-byte array.')
    if len(pubkey) != 32:
        raise ValueError('The public key must be a 32-byte array.')
    if len(sig) != 64:
        raise ValueError('The signature must be a 64-byte array.')

    P = point_from_bytes(pubkey)
    if (P is None):
        return False

    r = int.from_bytes(sig[:32], byteorder="big")
    s = int.from_bytes(sig[32:], byteorder="big")
    if (r >= p or s >= n):
        return False

    e = int.from_bytes(
        tagged_hash("BIPSchnorr", sig[0:32] + pubkey + msg), byteorder="big"
    ) % n
    R = Point(*(G * s + point_mul(P, n - e)))  # P*(n-e) does not work...
    if R is None or not is_quad(R.y) or R.x != r:
        return False

    return True


class Point(list):
    """
    ``secp256k1`` point . Initialization can be done with sole ``x`` value.
    :class:`Point` overrides ``*`` and ``+`` operators which accepts
    :class:`list` as argument and returns :class:`Point`.
    """

    x = property(
        lambda cls: list.__getitem__(cls, 0),
        lambda cls, v: [
            list.__setitem__(cls, 0, int(v)),
            list.__setitem__(cls, 1, y_from_x(int(v)))
        ],
        None, "Return list item #0"
    )
    y = property(
        lambda cls: list.__getitem__(cls, 1),
        None, None, "Return list item #1"
    )

    def __init__(self, *xy):
        if len(xy) == 0:
            xy = (0, None)
        elif len(xy) == 1:
            xy += (y_from_x(int(xy[0])), )
        list.__init__(self, [int(e) if e is not None else e for e in xy[:2]])

    def __mul__(self, k):
        if isinstance(k, int):
            return Point(*point_mul(self, k))
        else:
            raise TypeError("'%s' should be an int" % k)
    __rmul__ = __mul__

    def __add__(self, P):
        if isinstance(P, list):
            return Point(*point_add(self, P))
        else:
            raise TypeError("'%s' should be a 2-int-length list" % P)
    __radd__ = __add__

    def __repr__(self):
        return "<secp256k1 point:\n  x:%064x\n  y:%064x\n>" % tuple(self)


G = Point(0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798)
