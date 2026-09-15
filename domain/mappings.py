"""
Mapeamento dos códigos das variáveis (Value (VAR_COD_POR_VALUE).

100% IDÊNTICO ao do monólito (linha 2672-2704 backup).
NÃO adicionar/remover mapeamentos — hardcoded aqui
mapeamento VALUE → CÓDIGO (value do checkbox PrimeFaces → código humano ex: 955 → 17).
"""
from __future__ import annotations

# -------------------------------------------------------------------
# VAR_COD_POR_VALUE[value_checkbox] = codigo_variavel
# Extraído VERBATIM do monólito backup.
# -------------------------------------------------------------------
VAR_COD_POR_VALUE: dict[str, str] = {
    "955": "17",   # Margem de Lucro Operacional (padrão marcado)
    "956": "21",   # Situação Financeira da Empresa (padrão marcado)
    "957": "23",   # Acesso ao Crédito da Empresa (padrão marcado)
    "958": "25",   # Preço médio matérias-primas (padrão marcado)
    "52100": "0",    # coment - comentários
    "971": "1",     # COND - cond. atuais
    "953": "2",     # EXPEC - exp. atuais
    "972": "3",     # ICEI
    "53103": "4",    # IceiEst
    "53101": "5",    # IndCondEst
    "53102": "6",    # IndExpecEst
    "946": "7",      # PA - cond. economia
    "950": "8",      # PB - cond. setor
    "947": "9",      # PC - cond. empresa
    "943": "10",     # PD - exp. economia
    "951": "11",     # PE - exp. setor
    "949": "12",     # PF - exp. empresa
    "944": "13",     # PG - cond. estado
    "945": "14",     # PH - exp. estado
    "954": "15",     # pp - principais problemas 1
    "948": "16",     # (sem letra)
    "969": "18",     # p10 - quant. exportada
    "970": "19",     # p11 - intenção investimento 6m
    "961": "20",     # p2 - UCI efetiva
    "962": "22",     # p3 - utilização capacidade
    "963": "24",     # p4 - evolução num. empregados
    "965": "26",     # p5 - estoques planejados
    "966": "27",     # p6 - estoques evolução
    "964": "28",     # p7 - demanda
    "967": "29",     # p8 - núm. empregados
    "968": "30",     # p9 - compras mat prima
}


# Mapping invertido (código_variavel → value_checkbox
# Derivado de VAR_COD_POR_VALUE acima
def codigo_para_value(cod_variavel: str) -> str | None:
    """Retorna o value (do checkbox para um código de variável (ex: "17" → "955")."""
    for val, cod in VAR_COD_POR_VALUE.items():
        if cod == cod_variavel:
            return val
    return None


def codigos_para_values(codigos_variaveis: list[str]) -> list[str]:
    """Converte uma lista códigos humanos → lista de values de checkbox, filtrando None."""
    res: list[str] = []
    for cod in codigos_variaveis:
        v = codigo_para_value(cod)
        if v is not None:
            res.append(v)
    return res


__all__ = ["VAR_COD_POR_VALUE", "codigo_para_value", "codigos_para_values"]
