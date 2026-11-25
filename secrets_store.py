"""Encrypt tokens at rest. On Windows uses user-bound DPAPI; on other OS, passphrase-derived Fernet."""
import base64
import ctypes
import json
import os
import secrets
import sys
import threading
from pathlib import Path
from ctypes import wintypes
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from messages import UserError

class TokenStore:
    def __init__(self, directory):
        self.path=Path(directory)/'tokens.enc'
        self._password=None
        self.lock=threading.RLock()

    @property
    def mode(self):
        return 'windows-dpapi' if sys.platform=='win32' else 'passphrase'

    def unlock(self, password):
        if self.mode=='windows-dpapi': return
        if not isinstance(password,str) or len(password)<12:
            raise UserError('err.masterShort')
        with self.lock:
            old=self._password
            self._password=password
            try: self.read()
            except Exception:
                self._password=old
                raise

    def _key(self,salt):
        if not self._password:
            raise UserError('err.storeLocked')
        data=PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000).derive(self._password.encode('utf-8'))
        return base64.urlsafe_b64encode(data)

    @staticmethod
    def _dpapi(data, encrypt=True):
        class BLOB(ctypes.Structure):
            _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]
        buf=ctypes.create_string_buffer(data)
        source=BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_byte)))
        dest=BLOB()
        crypt=ctypes.windll.crypt32
        fn=crypt.CryptProtectData if encrypt else crypt.CryptUnprotectData
        if encrypt:
            ok=fn(ctypes.byref(source),'ModFerry',None,None,None,1,ctypes.byref(dest))
        else:
            ok=fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(dest))
        if not ok: raise UserError('err.dpapi')
        try: return ctypes.string_at(dest.pbData,dest.cbData)
        finally: ctypes.windll.kernel32.LocalFree(dest.pbData)

    def read(self):
        with self.lock:
            if not self.path.exists(): return {}
            envelope=json.loads(self.path.read_text('utf-8'))
            blob=base64.b64decode(envelope['ciphertext'],validate=True)
            if envelope['scheme'] != self.mode:
                raise UserError('err.storeScheme')
            try:
                if self.mode=='windows-dpapi': raw=self._dpapi(blob,False)
                else: raw=Fernet(self._key(base64.b64decode(envelope['salt']))).decrypt(blob)
            except InvalidToken as exc:
                raise UserError('err.wrongPassword') from exc
            return json.loads(raw.decode('utf-8'))

    def write(self, items):
        with self.lock:
            raw=json.dumps(items).encode('utf-8')
            payload={'scheme':self.mode}
            if self.mode=='windows-dpapi': encrypted=self._dpapi(raw)
            else:
                salt=secrets.token_bytes(16)
                payload['salt']=base64.b64encode(salt).decode('ascii')
                encrypted=Fernet(self._key(salt)).encrypt(raw)
            payload['ciphertext']=base64.b64encode(encrypted).decode('ascii')
            temp=self.path.with_suffix('.tmp')
            with open(temp,'w',encoding='utf-8') as f:
                json.dump(payload,f)
            if os.name!='nt': os.chmod(temp,0o600)
            temp.replace(self.path)

    def status(self):
        try:
            if self.mode=='passphrase' and not self._password:
                return {'mode':self.mode,'locked':True,'curseforge':False,'modrinth':False}
            data=self.read()
            return {'mode':self.mode,'locked':False,'curseforge':bool(data.get('curseforge')),'modrinth':bool(data.get('modrinth'))}
        except ValueError:
            return {'mode':self.mode,'locked':True,'curseforge':False,'modrinth':False}
