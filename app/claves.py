"""Palabra clave opcional por usuario (modo "rostro + palabra clave").

Solo se guarda un hash scrypt con sal aleatoria (hashlib.scrypt, n=2^14, r=8, p=1), nunca la clave en texto plano.
Formato guardado en meta.json:  scrypt$<n>$<r>$<p>$<sal_b64>$<hash_b64>
La comparación usa hmac.compare_digest.
"""
import base64
import hashlib
import hmac
import os

from . import config as CFG

N, R, P, LARGO = 2 ** 14, 8, 1, 32


class ErrorClave(ValueError):
    pass


def validar(clave):
    if not isinstance(clave, str) or not CFG.CLAVE_MIN <= len(clave) <= CFG.CLAVE_MAX:
        raise ErrorClave(f"La palabra clave debe tener entre {CFG.CLAVE_MIN} y {CFG.CLAVE_MAX} caracteres.")
    return clave


def hashear(clave):
    validar(clave)
    sal = os.urandom(16)
    h = hashlib.scrypt(clave.encode("utf-8"), salt=sal, n=N, r=R, p=P, dklen=LARGO)
    return "scrypt${}${}${}${}${}".format(N, R, P, base64.b64encode(sal).decode(), base64.b64encode(h).decode())


def comprobar(clave, guardado):
    """True si `clave` corresponde al hash guardado. Nunca lanza con entradas raras: devuelve False."""
    try:
        alg, n, r, p, sal, h = guardado.split("$")
        if alg != "scrypt" or not isinstance(clave, str):
            return False
        calc = hashlib.scrypt(clave.encode("utf-8"), salt=base64.b64decode(sal), n=int(n), r=int(r), p=int(p),
                              dklen=len(base64.b64decode(h)))
        return hmac.compare_digest(calc, base64.b64decode(h))
    except (ValueError, AttributeError, TypeError):
        return False
