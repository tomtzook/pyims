import sys
from typing import Optional
import base64
import io
import hashlib
import random

from . import milenge
from .headers import Authorization, WWWAuthenticate
from .sip_types import AuthenticationScheme, AuthenticationAlgorithm, Method


class Account(object):

    def __init__(self,
                 mcc: int, mnc: int,
                 imsi: str,
                 sim_ki: str,
                 sim_op: Optional[str] = None,
                 sim_opc: Optional[str] = None,
                 sim_amf: Optional[str] = None):
        self.mcc = mcc
        self.mnc = mnc
        self.imsi = imsi
        self.sim_ki = bytes.fromhex(sim_ki)
        self.sim_op = bytes.fromhex(sim_op) if sim_op else None
        self.sim_opc = bytes.fromhex(sim_opc) if sim_opc else milenge.generate_opc(self.sim_ki, self.sim_op)
        self.sim_amf = bytes.fromhex(sim_amf)


class Authenticator(object):

    def __init__(self, account: Account, host: str):
        self._account = account
        self._host = host

    def create_auth_header(self, method: Method, requested_auth: Optional[WWWAuthenticate] = None) -> Authorization:
        username = f"{self._account.imsi}@{self._host}"
        realm = self._host
        uri = f"sip:{self._host}"
        auth_type = requested_auth.qop if requested_auth else 'auth'
        nc = None
        cnonce = None
        nonce = ''
        response = ''

        if requested_auth is not None:
            username = self._account.imsi
            nonce = requested_auth.nonce
            nonce_count = 1
            nc = f"{nonce_count:08d}"
            cnonce = hex(random.randint(0, sys.maxsize))[2:]

            response = self.create_auth_md5(
                username,
                self.create_password(self._account, nonce),
                realm,
                uri,
                method.name,
                nonce,
                nc,
                cnonce,
                auth_type
            )

        return Authorization(
            scheme=AuthenticationScheme.DIGEST,
            username=username,
            uri=uri,
            realm=realm,
            algorithm=AuthenticationAlgorithm.AKA,
            qop=auth_type,
            nc=nc,
            cnonce=cnonce,
            nonce=nonce,
            response=response
        )

    @staticmethod
    def create_auth_md5(username: str, password: bytes,
                        realm: str, uri: str, method: str,
                        nonce: str, nc: str, cnonce: str,
                        auth_type: str) -> str:
        a1 = hashlib.md5()
        a1.update(username.encode('utf-8'))
        a1.update(b':')
        a1.update(realm.encode('utf-8'))
        a1.update(b':')
        a1.update(password)
        a1 = a1.hexdigest()

        a2 = hashlib.md5()
        a2.update(method.encode('utf-8'))
        a2.update(b':')
        a2.update(uri.encode('utf-8'))
        a2 = a2.hexdigest()

        resp = hashlib.md5()
        resp.update(a1.encode('utf-8'))
        resp.update(b':')
        resp.update(nonce.encode('utf-8'))
        resp.update(b':')
        resp.update(nc.encode('utf-8'))
        resp.update(b':')
        resp.update(cnonce.encode('utf-8'))
        resp.update(b':')
        resp.update(auth_type.encode('utf-8'))
        resp.update(b':')
        resp.update(a2.encode('utf-8'))

        return resp.hexdigest()

    @staticmethod
    def create_password(account: Account, nonce: str) -> bytes:
        nonce_decoded = io.BytesIO(base64.b64decode(nonce))
        rand = nonce_decoded.read(16)
        sqnxoraka = nonce_decoded.read(6)
        amf = nonce_decoded.read(2)
        mac = nonce_decoded.read(8)

        res, ak = milenge.f2_f5(account.sim_ki, rand, account.sim_opc)
        # ck = milenge.f3(account.sim_ki, rand, account.sim_opc)
        # ik = milenge.f4(account.sim_ki, rand, account.sim_opc)

        sqn = milenge.xor(sqnxoraka, ak)
        xmac, _ = milenge.f1(account.sim_ki, sqn, rand, account.sim_opc, account.sim_amf)

        assert xmac == mac

        return res
