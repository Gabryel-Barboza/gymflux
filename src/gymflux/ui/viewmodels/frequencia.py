"""FrequenciaViewModel — consultas antifraude sobre o log (Qt-free)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from gymflux.core.acesso import DirecaoAcesso, ResultadoAcesso, TentativaAcesso
from gymflux.core.aluno import Aluno
from gymflux.core.caixa import validar_mes
from gymflux.core.funcionario import Funcionario


class FrequenciaLogProto(Protocol):
    def listar(self) -> list[TentativaAcesso]: ...
    def listar_por_aluno(self, aluno_id: str) -> list[TentativaAcesso]: ...


class FrequenciaAlunoProto(Protocol):
    def listar(self) -> list[Aluno]: ...
    def buscar_por_id(self, aluno_id: str) -> Aluno | None: ...


class FrequenciaFuncionarioProto(Protocol):
    def buscar_por_id(self, funcionario_id: str) -> Funcionario | None: ...


@dataclass
class FrequenciaViewModel:
    """Filtros dia/mês/aluno sobre tentativas + resumo por dia (presença = LIBERADO)."""

    log_repo: FrequenciaLogProto | None = None
    aluno_repo: FrequenciaAlunoProto | None = None
    funcionario_repo: FrequenciaFuncionarioProto | None = None

    def tentativas(self) -> list[TentativaAcesso]:
        if self.log_repo is None:
            return []
        return self.log_repo.listar()

    def filtrar(
        self,
        dia: date | None = None,
        mes: str | None = None,
        aluno_id: str | None = None,
    ) -> list[TentativaAcesso]:
        """Filtros combinados (AND); mes no formato AAAA-MM."""
        if mes is not None:
            validar_mes(mes)
        resultado = self.tentativas()
        if dia is not None:
            resultado = [t for t in resultado if t.timestamp.date() == dia]
        if mes is not None:
            resultado = [t for t in resultado if t.timestamp.strftime("%Y-%m") == mes]
        if aluno_id is not None:
            resultado = [t for t in resultado if t.aluno_id == aluno_id]
        return resultado

    def meses_disponiveis(self) -> list[str]:
        return sorted({t.timestamp.strftime("%Y-%m") for t in self.tentativas()}, reverse=True)

    def listar_alunos(self) -> list[Aluno]:
        if self.aluno_repo is None:
            return []
        return sorted(self.aluno_repo.listar(), key=lambda a: a.nome.lower())

    def nome_tentativa(self, tentativa: TentativaAcesso) -> str:
        if tentativa.funcionario_id:
            repo = self.funcionario_repo
            if repo is None:
                return tentativa.funcionario_id
            try:
                func = repo.buscar_por_id(tentativa.funcionario_id)
            except Exception:
                return tentativa.funcionario_id
            return func.nome if func is not None else tentativa.funcionario_id
        if tentativa.aluno_id and self.aluno_repo is not None:
            try:
                aluno = self.aluno_repo.buscar_por_id(tentativa.aluno_id)
            except Exception:
                return tentativa.aluno_id
            return aluno.nome if aluno is not None else tentativa.aluno_id
        return tentativa.aluno_id or "—"

    def resumo_por_dia(
        self, aluno_id: str, excluir_hoje: bool = True, hoje: date | None = None
    ) -> list[tuple[date, int, int]]:
        """[(dia, entradas, saídas)] LIBERADOS, desc; outros dias p/ o perfil."""
        if self.log_repo is None:
            return []
        ref = hoje or date.today()
        por_dia: dict[date, list[int]] = {}
        for t in self.log_repo.listar_por_aluno(aluno_id):
            dia = t.timestamp.date()
            if excluir_hoje and dia == ref:
                continue
            if t.resultado != ResultadoAcesso.LIBERADO:
                continue
            cont = por_dia.setdefault(dia, [0, 0])
            if t.direcao == DirecaoAcesso.ENTRADA:
                cont[0] += 1
            else:
                cont[1] += 1
        return sorted(
            ((d, c[0], c[1]) for d, c in por_dia.items()), key=lambda r: r[0], reverse=True
        )
