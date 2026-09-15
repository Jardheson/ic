"""
Testes unitários domain.models.PesquisaParams + validators (TR11).

Cenários:
  1) params default VÁLIDO (não levanta exceção)
  2) mes_inicio=13 → ValidationError (fora 0..11)
  3) orientacao="DIAGONAL" → ValidationError (fora {LINHA,COLUNA})
  4) codigos_variaveis=[] → ValidationError (lista vazia)
"""
from __future__ import annotations

import pytest

from domain.models import PesquisaParams
from core.errors import ValidationError
from config.constants import (
    DEFAULT_COORTE_VALUE,
    DEFAULT_MES_INICIO,
    DEFAULT_ANO_INICIO,
    DEFAULT_MES_FIM,
    DEFAULT_ANO_FIM,
    DEFAULT_VARIAVEIS_CODIGOS,
    DEFAULT_TIPO_ESTIMATIVA_VALUE,
    DEFAULT_EXIBICAO_BOOL,
    DEFAULT_ORIENTACAO_VALUE,
)


def _params_defaults(**overrides) -> dict:
    base = dict(
        coorte=DEFAULT_COORTE_VALUE,
        mes_inicio=DEFAULT_MES_INICIO,
        ano_inicio=DEFAULT_ANO_INICIO,
        mes_fim=DEFAULT_MES_FIM,
        ano_fim=DEFAULT_ANO_FIM,
        codigos_variaveis=list(DEFAULT_VARIAVEIS_CODIGOS),
        tipo_estimativa=DEFAULT_TIPO_ESTIMATIVA_VALUE,
        exibicao=DEFAULT_EXIBICAO_BOOL,
        orientacao=DEFAULT_ORIENTACAO_VALUE,
    )
    base.update(overrides)
    return base


def test_params_valido_sem_erro():
    p = PesquisaParams(**_params_defaults())
    assert p.coorte == DEFAULT_COORTE_VALUE
    assert p.mes_inicio == DEFAULT_MES_INICIO
    assert p.ano_inicio == DEFAULT_ANO_INICIO
    assert p.codigos_variaveis == list(DEFAULT_VARIAVEIS_CODIGOS)
    assert p.tipo_estimativa == DEFAULT_TIPO_ESTIMATIVA_VALUE
    assert p.exibicao is True
    assert p.orientacao == DEFAULT_ORIENTACAO_VALUE


def test_mes_inicio_13_validation_error():
    with pytest.raises(ValidationError) as exc:
        PesquisaParams(**_params_defaults(mes_inicio=13))
    assert "mês" in str(exc.value).lower() or "mes" in str(exc.value).lower()


def test_mes_fim_negativo_validation_error():
    with pytest.raises(ValidationError):
        PesquisaParams(**_params_defaults(mes_fim=-1))


def test_orientacao_invalida_diagonal():
    with pytest.raises(ValidationError) as exc:
        PesquisaParams(**_params_defaults(orientacao="DIAGONAL"))
    txt = str(exc.value).lower()
    assert "linha" in txt or "coluna" in txt or "orient" in txt


def test_codigos_variaveis_vazio_validation_error():
    with pytest.raises(ValidationError) as exc:
        PesquisaParams(**_params_defaults(codigos_variaveis=[]))
    assert "lista" in str(exc.value).lower() or "vaz" in str(exc.value).lower() or "código" in str(exc.value).lower()


def test_ano_fora_faixa_validation_error():
    with pytest.raises(ValidationError):
        PesquisaParams(**_params_defaults(ano_inicio=2150))


def test_tipo_estimativa_invalido():
    with pytest.raises(ValidationError):
        PesquisaParams(**_params_defaults(tipo_estimativa="99"))


def test_coorte_vazia_validation_error():
    with pytest.raises(ValidationError):
        PesquisaParams(**_params_defaults(coorte=""))
