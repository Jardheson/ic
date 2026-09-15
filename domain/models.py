"""
Modelos de domínio da aplicação (Pydantic v2).

- `PesquisaParams`: encapsula TODOS os parâmetros necessários para rodar
  uma pesquisa no site da CNI (FASE 3 do pipeline).
- Validações integradas via `field_validator` usando os validadores standalone
  de `domain.validators` — qualquer valor inválido levanta `core.errors.ValidationError`
  em tempo de construção do objeto (fail-fast).
"""
from __future__ import annotations

from typing import List

try:
    from pydantic import BaseModel, field_validator, ConfigDict
    _PYDANTIC_OK = True
except ImportError:  # pragma: no cover - fallback sem pydantic
    _PYDANTIC_OK = False
    BaseModel = object  # type: ignore[assignment,misc]

from domain.validators import (
    validar_ano,
    validar_coorte,
    validar_exibicao,
    validar_lista_codigos,
    validar_mes,
    validar_orientacao,
    validar_tipo_estimativa,
)


if _PYDANTIC_OK:

    class PesquisaParams(BaseModel):
        """
        Parâmetros de pesquisa do formulário selectForm (FASE 3).

        Ordem lógica de preenchimento (imposta em services/pesquisa_service.py):
          1. coorte → mes_inicio/ano_inicio → mes_fim/ano_fim
          2. estrato (codigos_variaveis aqui são variáveis; estrato fica fora)
          3. variaveis
          4. tipo_estimativa → exibicao → orientacao
          5. clicar_pesquisar
        """

        model_config = ConfigDict(frozen=True, extra="forbid")

        coorte: str
        mes_inicio: int
        ano_inicio: int
        mes_fim: int
        ano_fim: int
        codigos_variaveis: List[str]
        tipo_estimativa: str
        exibicao: bool
        orientacao: str

        # --- Validadores ---
        @field_validator("coorte", mode="before")
        @classmethod
        def _v_coorte(cls, v):
            return validar_coorte(v, campo="coorte")

        @field_validator("mes_inicio", "mes_fim", mode="before")
        @classmethod
        def _v_mes(cls, v, info):
            return validar_mes(int(v) if isinstance(v, str) and v.isdigit() else v, campo=info.field_name)

        @field_validator("ano_inicio", "ano_fim", mode="before")
        @classmethod
        def _v_ano(cls, v, info):
            return validar_ano(int(v) if isinstance(v, str) and v.isdigit() else v, campo=info.field_name)

        @field_validator("codigos_variaveis", mode="before")
        @classmethod
        def _v_codigos(cls, v):
            return validar_lista_codigos(v, campo="codigos_variaveis")

        @field_validator("tipo_estimativa", mode="before")
        @classmethod
        def _v_te(cls, v):
            return validar_tipo_estimativa(v, campo="tipo_estimativa")

        @field_validator("exibicao", mode="before")
        @classmethod
        def _v_exib(cls, v):
            if isinstance(v, str):
                s = v.strip().lower()
                if s in {"1", "true", "sim", "yes"}:
                    v = True
                elif s in {"0", "false", "nao", "não", "no"}:
                    v = False
            return validar_exibicao(v, campo="exibicao")

        @field_validator("orientacao", mode="before")
        @classmethod
        def _v_orient(cls, v):
            return validar_orientacao(v, campo="orientacao")

else:  # pragma: no cover - fallback dataclass manual se Pydantic não disponível
    from dataclasses import dataclass, field
    from typing import List as _List

    @dataclass(frozen=True)
    class PesquisaParams:  # type: ignore[no-redef]
        coorte: str
        mes_inicio: int
        ano_inicio: int
        mes_fim: int
        ano_fim: int
        codigos_variaveis: _List[str]
        tipo_estimativa: str
        exibicao: bool
        orientacao: str

        def __post_init__(self):
            object.__setattr__(self, "coorte", validar_coorte(self.coorte, campo="coorte"))
            object.__setattr__(self, "mes_inicio", validar_mes(self.mes_inicio, campo="mes_inicio"))
            object.__setattr__(self, "mes_fim", validar_mes(self.mes_fim, campo="mes_fim"))
            object.__setattr__(self, "ano_inicio", validar_ano(self.ano_inicio, campo="ano_inicio"))
            object.__setattr__(self, "ano_fim", validar_ano(self.ano_fim, campo="ano_fim"))
            object.__setattr__(
                self,
                "codigos_variaveis",
                validar_lista_codigos(self.codigos_variaveis, campo="codigos_variaveis"),
            )
            object.__setattr__(
                self,
                "tipo_estimativa",
                validar_tipo_estimativa(self.tipo_estimativa, campo="tipo_estimativa"),
            )
            object.__setattr__(self, "exibicao", validar_exibicao(self.exibicao, campo="exibicao"))
            object.__setattr__(
                self, "orientacao", validar_orientacao(self.orientacao, campo="orientacao")
            )


__all__ = ["PesquisaParams"]
