"""AlunosViewModel — cadastro, busca, bloqueio e matrícula (Qt-free)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from gymflux.core.aluno import Aluno, StatusAluno
from gymflux.core.plano import Matricula, Plano, Vigencia
from gymflux.services.cadastrar_aluno import CadastrarAlunoService


class MatriculaRepoProto(Protocol):
    def salvar(self, matricula: Matricula, matricula_id: str | None = None) -> Matricula: ...
    def listar_por_aluno(self, aluno_id: str) -> list[Matricula]: ...
    def remover(self, matricula_id: str) -> None: ...


class PlanoRepoProto(Protocol):
    def buscar_por_id(self, plano_id: str) -> Plano | None: ...
    def listar(self) -> list[Plano]: ...


@dataclass
class AlunosViewModel:
    alunos: CadastrarAlunoService
    commit: Callable[[], None] | None = None
    matricula_repo: MatriculaRepoProto | None = None
    plano_repo: PlanoRepoProto | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    # -- listagem com filtros da tela ----------------------------------------
    def listar(self, busca: str = "", status: StatusAluno | None = None) -> list[Aluno]:
        termo = busca.strip().lower()
        digits = "".join(c for c in busca if c.isdigit())
        result: list[Aluno] = []
        for aluno in self.alunos.listar():
            if status is not None and aluno.status != status:
                continue
            if termo:
                nome_ok = termo in aluno.nome.lower()
                cpf_digits = "".join(c for c in (aluno.cpf or "") if c.isdigit())
                cpf_ok = bool(digits) and digits in cpf_digits
                if not (nome_ok or cpf_ok):
                    continue
            result.append(aluno)
        return sorted(result, key=lambda a: a.nome.lower())

    # -- CRUD -----------------------------------------------------------------
    def cadastrar(
        self,
        *,
        nome: str,
        cpf: str | None = None,
        data_nasc: date | None = None,
        telefone: str | None = None,
        email: str | None = None,
        observacoes: str | None = None,
        endereco: str | None = None,
        senha: str | None = None,
    ) -> Aluno:
        aluno = Aluno(
            id=f"aluno-{uuid.uuid4().hex[:8]}",
            nome=nome.strip(),
            cpf=(cpf.strip() or None) if cpf else None,
            data_nasc=data_nasc,
            telefone=(telefone.strip() or None) if telefone else None,
            email=(email.strip() or None) if email else None,
            observacoes=(observacoes.strip() or None) if observacoes else None,
            endereco=(endereco.strip() or None) if endereco else None,
        )
        if senha and senha.strip():
            aluno.definir_senha(senha)  # ValueError se fora de 4-8 dígitos
        result = self.alunos.cadastrar(aluno)
        self._commit()
        return result

    def atualizar(
        self,
        aluno_id: str,
        *,
        nome: str,
        cpf: str | None = None,
        data_nasc: date | None = None,
        telefone: str | None = None,
        email: str | None = None,
        observacoes: str | None = None,
        endereco: str | None = None,
        senha: str | None = None,
        status: StatusAluno | None = None,
    ) -> Aluno:
        """Atualiza todos os campos editáveis; senha vazia mantém a atual."""
        aluno = self.alunos.buscar(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        if not nome or not nome.strip():
            raise ValueError("nome não pode ser vazio")
        aluno.nome = nome.strip()
        aluno.cpf = (cpf.strip() or None) if cpf else None
        aluno.data_nasc = data_nasc
        aluno.telefone = (telefone.strip() or None) if telefone else None
        aluno.email = (email.strip() or None) if email else None
        aluno.observacoes = (observacoes.strip() or None) if observacoes else None
        aluno.endereco = (endereco.strip() or None) if endereco else None
        if senha and senha.strip():
            aluno.definir_senha(senha)  # ValueError se fora de 4-8 dígitos
        if status is not None:
            aluno.status = status
            if status != StatusAluno.BLOQUEADO:
                aluno.bloqueado_manual = False
        result = self.alunos.atualizar(aluno)
        self._commit()
        return result

    def bloquear(self, aluno_id: str) -> Aluno:
        result = self.alunos.bloquear(aluno_id)
        self._commit()
        return result

    def desbloquear(self, aluno_id: str) -> Aluno:
        result = self.alunos.desbloquear(aluno_id)
        self._commit()
        return result

    def inativar(self, aluno_id: str) -> Aluno:
        result = self.alunos.inativar(aluno_id)
        self._commit()
        return result

    def reativar(self, aluno_id: str) -> Aluno:
        aluno = self.alunos.buscar(aluno_id)
        if aluno is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        aluno.reativar()
        result = self.alunos.atualizar(aluno)
        self._commit()
        return result

    # -- matrícula (liga aluno <-> plano p/ liberar catraca) -------------------
    def planos_disponiveis(self) -> list[Plano]:
        if self.plano_repo is None:
            return []
        return sorted(self.plano_repo.listar(), key=lambda p: p.nome.lower())

    def matriculas_do_aluno(self, aluno_id: str) -> list[Matricula]:
        if self.matricula_repo is None:
            return []
        return self.matricula_repo.listar_por_aluno(aluno_id)

    def matricular(self, aluno_id: str, plano_id: str, inicio: date | None = None) -> Matricula:
        if self.matricula_repo is None or self.plano_repo is None:
            raise RuntimeError("Repositórios de matrícula/plano não injetados")
        if self.alunos.buscar(aluno_id) is None:
            raise ValueError(f"Aluno id={aluno_id} não encontrado")
        plano = self.plano_repo.buscar_por_id(plano_id)
        if plano is None:
            raise ValueError(f"Plano id={plano_id} não encontrado")
        vigencia = Vigencia.a_partir_de(inicio or date.today(), plano.duracao_dias)
        matricula = Matricula(aluno_id=aluno_id, plano=plano, vigencia=vigencia, ativa=True)
        self.matricula_repo.salvar(matricula, matricula_id=f"mat-{uuid.uuid4().hex[:8]}")
        self._commit()
        return matricula

    def matriculas_com_id(self, aluno_id: str) -> list[tuple[str, Matricula]]:
        """Retorna (id, Matricula) p/ exibir e excluir; funciona com SQL e memória."""
        if self.matricula_repo is None:
            return []
        # memória: inspect _matriculas dict
        if hasattr(self.matricula_repo, "_matriculas"):
            try:
                dic = self.matricula_repo._matriculas  # type: ignore[attr-defined]
                return [(mid, m) for mid, m in dic.items() if m.aluno_id == aluno_id]  # type: ignore[attr-defined]
            except Exception:
                pass
        # SQLAlchemy: query via session se disponível
        if hasattr(self.matricula_repo, "session"):
            try:
                from sqlalchemy import select

                from gymflux.infra.models.matricula import MatriculaModel

                sess = self.matricula_repo.session  # type: ignore[attr-defined]
                stmt = select(MatriculaModel).where(MatriculaModel.aluno_id == aluno_id)
                modelos = sess.execute(stmt).scalars().all()  # type: ignore[attr-defined]
                out: list[tuple[str, Matricula]] = []
                for mm in modelos:
                    plano = None
                    # resolve plano via repo helper if exists
                    if hasattr(self.matricula_repo, "_get_plano_domain"):
                        plano = self.matricula_repo._get_plano_domain(mm.plano_id)  # type: ignore[attr-defined]
                    if plano is not None:
                        from gymflux.core.plano import Vigencia as Vig

                        out.append(
                            (
                                mm.id,
                                Matricula(
                                    aluno_id=mm.aluno_id,
                                    plano=plano,
                                    vigencia=Vig(inicio=mm.inicio, fim=mm.fim),
                                    ativa=bool(mm.ativa),
                                ),
                            )
                        )
                if out:
                    return out
            except Exception:
                pass
        # fallback: listar sem id (gera ids sintéticos não removíveis — último recurso)
        return [(f"idx-{i}", m) for i, m in enumerate(self.matriculas_do_aluno(aluno_id))]

    def remover_matricula(self, matricula_id: str) -> None:
        if self.matricula_repo is None:
            raise RuntimeError("Repositório de matrícula não injetado")
        # ignora ids sintéticos idx-*
        if matricula_id.startswith("idx-"):
            raise ValueError("Matrícula sem ID persistido não pode ser removida")
        self.matricula_repo.remover(matricula_id)
        self._commit()
