from __future__ import annotations

import hashlib
import os

from gms_app.hardware.biometric.interface import BiometricDriver, TemplateBiometrico


class MockBiometricDriver(BiometricDriver):
    is_mock = True

    def __init__(self) -> None:
        self._store: dict[int, TemplateBiometrico] = {}

    def cadastrar(self, aluno_id: int) -> TemplateBiometrico:
        fake = hashlib.sha256(os.urandom(16)).digest()[:256]
        t = TemplateBiometrico(aluno_id=aluno_id, template=fake, qualidade=90)
        self._store[aluno_id] = t
        return t

    def verificar(self, template: bytes) -> int | None:
        for tid, t in self._store.items():
            if t.template == template:
                return tid
        return None

    def remover(self, aluno_id: int) -> None:
        self._store.pop(aluno_id, None)
