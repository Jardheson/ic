"""
Validadores de domínio para parâmetros de pesquisa CNI.

Todos os validadores são standalone (puros) — não tocam no navegador.
Em caso de valor inválido, levantam `core.errors.ValidationError` (NÃO retryable).
"""
from __future__ import annotations

from typing import Iterable, List

from core.errors import ValidationError


def validar_mes(mes: int, *, campo: str = "mes") -> int:
    """
    Valida mês (0-indexado: 0 = Janeiro, 11 = Dezembro, conforme PrimeFaces).

    Raises:
        ValidationError: Se mes não for int entre 0 e 11 inclusive.
    """
    if not isinstance(mes, int):
        raise ValidationError(
            f"{campo}: deve ser inteiro (0-11), recebido {type(mes).__name__}={mes!r}"
        )
    if mes < 0 or mes > 11:
        raise ValidationError(
            f"{campo}: deve estar entre 0 (Janeiro) e 11 (Dezembro), recebido={mes}"
        )
    return mes


def validar_ano(ano: int, *, campo: str = "ano", min_ano: int = 1990, max_ano: int = 2100) -> int:
    """
    Valida ano: inteiro de 4 dígitos entre min_ano e max_ano.

    Raises:
        ValidationError: Se ano não for int ou estiver fora da faixa.
    """
    if not isinstance(ano, int):
        raise ValidationError(
            f"{campo}: deve ser inteiro, recebido {type(ano).__name__}={ano!r}"
        )
    if ano < min_ano or ano > max_ano:
        raise ValidationError(
            f"{campo}: deve estar entre {min_ano} e {max_ano}, recebido={ano}"
        )
    return ano


def validar_lista_codigos(codigos: Iterable[str], *, campo: str = "codigos") -> List[str]:
    """
    Valida lista de códigos de variáveis/estratos: não vazia, todos strs não-vazios.

    Raises:
        ValidationError: Se vazia ou contiver itens inválidos.
    """
    lista: List[str] = []
    try:
        iteravel = list(codigos)
    except TypeError as exc:
        raise ValidationError(
            f"{campo}: iterável inválida ({type(codigos).__name__})"
        ) from exc

    if len(iteravel) == 0:
        raise ValidationError(f"{campo}: lista não pode ser vazia")

    for i, item in enumerate(iteravel):
        if not isinstance(item, str):
            raise ValidationError(
                f"{campo}[{i}]: deve ser string, recebido {type(item).__name__}={item!r}"
            )
        s = item.strip()
        if not s:
            raise ValidationError(f"{campo}[{i}]: string vazia")
        lista.append(s)
    return lista


def validar_coorte(coorte: str, *, campo: str = "coorte") -> str:
    """Valida coorte: string não-vazia (geralmente numérica como "634")."""
    if not isinstance(coorte, str):
        raise ValidationError(
            f"{campo}: deve ser string, recebido {type(coorte).__name__}={coorte!r}"
        )
    s = coorte.strip()
    if not s:
        raise ValidationError(f"{campo}: string vazia")
    return s


def validar_tipo_estimativa(valor: str, *, campo: str = "tipo_estimativa") -> str:
    """Valida tipo_estimativa: atualmente só "21" (Frequência) é usado."""
    if not isinstance(valor, str):
        raise ValidationError(
            f"{campo}: deve ser string, recebido {type(valor).__name__}={valor!r}"
        )
    s = valor.strip()
    if not s:
        raise ValidationError(f"{campo}: string vazia")
    permitidos = {"21", "22"}
    if s not in permitidos:
        raise ValidationError(
            f"{campo}: valor={s!r} não permitido; permitidos={sorted(permitidos)}"
        )
    return s


def validar_orientacao(valor: str, *, campo: str = "orientacao") -> str:
    """Valida orientação: somente "LINHA" ou "COLUNA"."""
    if not isinstance(valor, str):
        raise ValidationError(
            f"{campo}: deve ser string, recebido {type(valor).__name__}={valor!r}"
        )
    s = valor.strip().upper()
    permitidos = {"LINHA", "COLUNA"}
    if s not in permitidos:
        raise ValidationError(
            f"{campo}: valor={valor!r} não permitido; permitidos={sorted(permitidos)}"
        )
    return s


def validar_exibicao(valor: bool, *, campo: str = "exibicao") -> bool:
    """Valida exibição: booleano (True = Valor, False = Variação)."""
    if not isinstance(valor, bool):
        raise ValidationError(
            f"{campo}: deve ser booleano, recebido {type(valor).__name__}={valor!r}"
        )
    return valor


__all__ = [
    "validar_mes",
    "validar_ano",
    "validar_lista_codigos",
    "validar_coorte",
    "validar_tipo_estimativa",
    "validar_orientacao",
    "validar_exibicao",
]
