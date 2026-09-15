"""
Constantes de UI e perfis de espera e velocidade de automação.
100% EXTRAÍDO DO MONÓLITO ORIGINAL (main_monolith_backup.py
LINHA 111-118 (perfis) e constantes de IDs JSF.

NÃO ALTERAR VALORES — qualquer mudança aqui afeta paridade funcional.
"""
from __future__ import annotations

# ====================================================================
# Perfis de velocidade/aguardar_pagina_pronta (100% idêntico ao monólito)
# ====================================================================
PERFIS: dict[str, dict[str, object]] = {
    "instantaneo": {"janela": 0.00, "hash_janela": 0.00, "poll": 0.015, "timeout": 3,  "usar_hash": False, "overlay_escape": 4.0},
    "leve":       {"janela": 0.005,"hash_janela": 0.00, "poll": 0.015, "timeout": 5,  "usar_hash": False, "overlay_escape": 5.0},
    "rapido":     {"janela": 0.02, "hash_janela": 0.00, "poll": 0.02,  "timeout": 7,  "usar_hash": False, "overlay_escape": 6.0},
    "navegacao":  {"janela": 0.05, "hash_janela": 0.02, "poll": 0.025, "timeout": 12, "usar_hash": True,  "overlay_escape": 8.0},
    "normal":     {"janela": 0.08, "hash_janela": 0.04, "poll": 0.03,  "timeout": 18, "usar_hash": True,  "overlay_escape": 10.0},
    "estrito":    {"janela": 0.15, "hash_janela": 0.08, "poll": 0.04,  "timeout": 30, "usar_hash": True,  "overlay_escape": 14.0},
}

# ====================================================================
# URLs e páginas alvo da CNI (Sondagens Industriais)
# ====================================================================
URL_BASE_LOGIN: str = "https://pesquisasconjunturais.cni.com.br/Sondagens/view/index.faces"

# ====================================================================
# Locators da TELA DE LOGIN (IDs exatos do monólito fazer_login_turbo)
# ====================================================================
LOGIN_FORM_ID: str = "loginForm"
LOGIN_USUARIO_SELECTOR: str = (
    "#loginForm\\:formLogin_usuarioInput, input[type='text'], input[id*='username' i], input[id*='login' i]"
)
LOGIN_SENHA_SELECTOR: str = "#loginForm\\:formLogin_senhaInput, input[type='password']"
LOGIN_SUBMIT_BTN_ID: str = "loginForm:formLogin_btnLogin"

# ====================================================================
# Locators da FASE 2: Navegação menus (IDs ESTÁTICOS mg11200/02/03)
# ====================================================================
LOCATOR_MENU_SONDAGEM_INDUSTRIAL = (
    "xpath",
    "//button[contains(@class,'buttonSelecaoPesquisa') and span[@class='ui-button-text ui-c'][.='Sondagem Industrial']]",
)
LOCATOR_MENU_CONSULTAS = ("css", "li[id='menuForm:mg11200'] > a.ui-menuitem-link")
LOCATOR_MENU_RESULTADOS = ("css", "li[id='menuForm:mg11202'] > a.ui-menuitem-link")
LOCATOR_MENU_FEDERACAO = ("css", "li[id='menuForm:mg11203'] > a.ui-menuitem-link")
LOCATOR_SUBMENU_FEDERACAO_FILHO = (
    "css", "li[id='menuForm:mg11203'] ul.ui-menu-child > li"
)
LOCATOR_FORM_MENU: str = "menuForm"

# ====================================================================
# Locators FASE 3: Formulário de Parâmetros (selectForm)
#   TODOS usam By.ID para IDs JSF com DOIS-PONTOS (:) — Constraint Business-C2
# ====================================================================
PARAM_FORM_ID: str = "selectForm"

LOCATOR_PARAM_COORTE_INPUT: str = "selectForm:coorte_input"
LOCATOR_PARAM_MES_INICIO_INPUT: str = "selectForm:mesInicio_input"
LOCATOR_PARAM_ANO_INICIO_INPUT: str = "selectForm:anoInicio_input"
LOCATOR_PARAM_MES_FIM_INPUT: str = "selectForm:mesFim_input"
LOCATOR_PARAM_ANO_FIM_INPUT: str = "selectForm:anoFim_input"

# Widgets SelectCheckboxMenu (bases para abrir painel scbmenu)
WIDGET_ESTRATO_BASE_ID: str = "selectForm:extrato"
WIDGET_VARIAVEIS_BASE_ID: str = "selectForm:variavel"

# Labels preferenciais do Estrato (100% idênticas ao monólito linha 2455-2457)
ESTRATO_PREFERENCIA_LABELS: list[str] = [
    "todas", "geral", "total", "indústria geral",
    "industria geral", "todas as empresas",
    "todos os estratos", "todos",
]

# Radio buttons FASE 3.3 / 3.4
RADIO_TIPO_ESTIMATIVA_TABLE_ID: str = "selectForm:tipoEstimativa"
RADIO_TIPO_ESTIMATIVA_VALUE_FREQUENCIA: str = "21"

RADIO_EXIBICAO_TABLE_ID: str = "selectForm:exibicao"
RADIO_EXIBICAO_VALUE_VALOR: str = "true"
RADIO_EXIBICAO_VALUE_VARIACAO: str = "false"

RADIO_ORIENTACAO_TABLE_ID: str = "selectForm:orientacao"
RADIO_ORIENTACAO_VALUE_LINHA: str = "LINHA"
RADIO_ORIENTACAO_VALUE_COLUNA: str = "COLUNA"

# Botão Pesquisar ID ESTÁTICO
BTN_PESQUISAR_ID: str = "selectForm:pesquisar"

# ====================================================================
# Locators FASE 4: Tabela de resultados + Exportar Excel
# ====================================================================
DATATABLE_RESULTADOS_ID: str = "listDifusaoLinhaForm:indicesVariavelDataTable"
EXPORT_EXCEL_LINK_ID: str = "listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140"
EXPORT_EXCEL_TITLE_SELECTOR: str = (
    "a[id='listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140'],"
    "a[title='Exportar resultados para um arquivo de planilha do Excel'],"
    "a.ui-commandlink"
)

# ====================================================================
# Valores DEFAULT padrão de pesquisa (hardcoded pipeline de produção)
#   Usados em services/pesquisa_service.py e no novo main.py
#   (100% identicos aos defaults do monólito)
# ====================================================================
DEFAULT_COORTE_VALUE: str = "634"
DEFAULT_COORTE_LABEL: str = "Ceará"

DEFAULT_MES_INICIO: int = 5
DEFAULT_ANO_INICIO: int = 2026
DEFAULT_MES_FIM: int = 7
DEFAULT_ANO_FIM: int = 2026

# ====================================================================
# Padrão ATUALIZADO: TODAS as 15 variáveis da tela (imagem usuário 2026-09-15).
#   p1 (Volume produção), p1t (Margem Lucro), p10 (Quant.export), p11 (Invest.),
#   p2 (UCI efetiva), p2t (Sit.Financ.), p3 (UCI capacidade), p3t (Acesso Crédito),
#   p4 (Evol.empregados), p4t (Preço MP), p5 (Estoq.planejados),
#   p6 (Estoq.evolução), p7 (Demanda), p8 (Nº empregados), p9 (Compras MP).
# ====================================================================
DEFAULT_VARIAVEIS_CODIGOS: list[str] = [
    "17",  # p1t Margem de Lucro Operacional
    "18",  # p10 Quantidade exportada
    "19",  # p11 Intenção investimento 6m
    "20",  # p2  UCI efetiva/usual
    "21",  # p2t Situação Financeira
    "22",  # p3  UCI capacidade instalada %
    "23",  # p3t Acesso ao Crédito
    "24",  # p4  Evolução empregados
    "25",  # p4t Preço médio matérias-primas
    "26",  # p5  Estoques planejados
    "27",  # p6  Estoques evolução nível
    "28",  # p7  Demanda por produtos
    "29",  # p8  Número empregados
    "30",  # p9  Compras matéria-prima
    "16",  # p1  Volume produção (fallback mapeamento: 948->16)
]
DEFAULT_VARIAVEIS_MODO: str = "lista_valores"  # "todas" / "lista_valores" / "preferencia"
DEFAULT_VARIAVEIS_USAR_MODO_TODAS: bool = False  # SOMENTE as 15 codigos da imagem, não 32

DEFAULT_TIPO_ESTIMATIVA_VALUE: str = RADIO_TIPO_ESTIMATIVA_VALUE_FREQUENCIA
DEFAULT_EXIBICAO_BOOL: bool = True
DEFAULT_ORIENTACAO_VALUE: str = RADIO_ORIENTACAO_VALUE_LINHA

# ====================================================================
# SEGURANÇA (Helpers em core/security.py — valores padrão aqui)
# ====================================================================
URL_WHITELIST: set[str] = {"pesquisasconjunturais.cni.com.br"}
WATCHDOG_TIMEOUT_GLOBAL_S: int = 60 * 60  # 60 minutos (antes era 30 — ajustado p/ 2 retries com folga)
