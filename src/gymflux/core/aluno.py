"""Entidade Aluno — domínio puro, sem I/O."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class StatusAluno(StrEnum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    BLOQUEADO = "BLOQUEADO"


SENHA_MIN_DIGITOS = 4
SENHA_MAX_DIGITOS = 8
_PBKDF2_ITERACOES = 100_000  # default prod — NÃO reduzir (segurança)
_ENV_PBKDF2_ITERACOES = "GYMFLUX_PBKDF2_ITERATIONS"
_HASH_PREFIXO = "pbkdf2_sha256"


def _iteracoes_pbkdf2() -> int:
    """Iterações do PBKDF2 — lê o env a cada chamada.

    Gancho de testabilidade: a suite fixa ``GYMFLUX_PBKDF2_ITERATIONS`` baixo
    via fixture autouse (ver ``tests/conftest.py``). Em prod a variável não
    existe e o default 100_000 vale sempre. Valor inválido => default.
    """
    try:
        return max(1, int(os.environ.get(_ENV_PBKDF2_ITERACOES, "") or _PBKDF2_ITERACOES))
    except ValueError:
        return _PBKDF2_ITERACOES


def validar_senha_numerica(senha: str) -> str:
    """Valida senha estilo SCA: 4-8 dígitos, só dígitos. Retorna normalizada."""
    digitos = senha.strip()
    if not digitos.isdigit() or not SENHA_MIN_DIGITOS <= len(digitos) <= SENHA_MAX_DIGITOS:
        raise ValueError(
            f"senha deve ter {SENHA_MIN_DIGITOS}-{SENHA_MAX_DIGITOS} dígitos numéricos"
        )
    return digitos


def gerar_senha_hash(senha: str, salt: bytes | None = None) -> str:
    """Gera hash com salt (PBKDF2-HMAC-SHA256). Nunca persiste texto puro."""
    digitos = validar_senha_numerica(senha)
    sal = salt if salt is not None else secrets.token_bytes(16)
    n = _iteracoes_pbkdf2()
    dk = hashlib.pbkdf2_hmac("sha256", digitos.encode(), sal, n)
    return f"{_HASH_PREFIXO}${n}${sal.hex()}${dk.hex()}"


def conferir_senha(senha: str, senha_hash: str | None) -> bool:
    """Confere senha contra hash. Formato desconhecido/nulo => False (nunca levanta)."""
    if not senha_hash:
        return False
    try:
        prefixo, iter_s, sal_hex, hash_hex = senha_hash.split("$")
        if prefixo != _HASH_PREFIXO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", senha.strip().encode(), bytes.fromhex(sal_hex), int(iter_s)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


@dataclass(slots=True)
class Aluno:
    """Aluno da academia.

    - `bloqueado_manual` sobrepõe qualquer liberação (RB03).
    - `status == BLOQUEADO` também é bloqueio manual (compat).
    """

    id: str
    nome: str
    cpf: str | None = None
    data_nasc: date | None = None
    telefone: str | None = None
    email: str | None = None
    status: StatusAluno = StatusAluno.ATIVO
    observacoes: str | None = None
    bloqueado_manual: bool = False
    senha_hash: str | None = None
    cartao_id: str | None = None

    def __post_init__(self) -> None:
        if not self.nome or not self.nome.strip():
            raise ValueError("nome não pode ser vazio")
        if self.cpf is not None:
            cpf_digits = "".join(c for c in self.cpf if c.isdigit())
            if cpf_digits and len(cpf_digits) != 11:
                raise ValueError("CPF deve ter 11 dígitos quando informado")

    @property
    def esta_bloqueado(self) -> bool:
        return self.bloqueado_manual or self.status == StatusAluno.BLOQUEADO

    @property
    def esta_ativo(self) -> bool:
        return self.status == StatusAluno.ATIVO and not self.bloqueado_manual

    def bloquear_manual(self) -> None:
        self.bloqueado_manual = True

    def desbloquear_manual(self) -> None:
        self.bloqueado_manual = False
        if self.status == StatusAluno.BLOQUEADO:
            self.status = StatusAluno.ATIVO

    def inativar(self) -> None:
        self.status = StatusAluno.INATIVO

    def reativar(self) -> None:
        if self.status == StatusAluno.INATIVO:
            self.status = StatusAluno.ATIVO

    # -- credenciais estilo SCA (senha numérica / cartão) ----------------------
    def definir_senha(self, senha: str) -> None:
        """Define senha numérica (4-8 dígitos); armazena só o hash com salt."""
        self.senha_hash = gerar_senha_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return conferir_senha(senha, self.senha_hash)

    def definir_cartao(self, cartao_id: str | None) -> None:
        cid = (cartao_id or "").strip()
        self.cartao_id = cid or None

    @property
    def tem_credencial(self) -> bool:
        return bool(self.senha_hash or self.cartao_id)
