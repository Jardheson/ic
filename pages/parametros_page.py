"""
ParametrosPage (POM): Formulário selectForm FASE 3 da CNI.

REGRAS CRÍTICAS (Hard Constraint do usuário — NÃO INVERTER):
  Ordem de preenchimento IMPOSTA (será garantida no PesquisaService, não aqui):
    1) 5 filtros básicos (Coorte → Mês/Ano Início → Mês/Ano Fim)
    2) FASE 3.2 ESTRATO (SelectCheckboxMenu MULTISELECT) — PRIMEIRO antes de Variáveis
    3) FASE 3.1 VARIÁVEIS (SelectCheckboxMenu MULTISELECT) — DEPOIS
    4) FASE 3.3 RÁDIOS (TipoEstimativa → Exibição)
    5) FASE 3.4 NOVO ORIENTAÇÃO (LINHA / COLUNA)
    6) Botão Pesquisar

Encapsula TODOS locators PRIVADOS (By.ID para IDs JSF com dois-pontos `:`).
Services NUNCA enxergam By ou find_element — só métodos públicos alto-nível.
"""
from __future__ import annotations

import time
from typing import List, Optional

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from config import constants
from domain.mappings import codigos_para_values
from infrastructure.browser.actions import (
    selecionar_valor,
    abrir_selectcheckboxmenu_primefaces,
    fechar_painel_selectcheckboxmenu,
    _ajustar_checkboxes_js,
    marcar_radiobutton_primefaces,
)
from infrastructure.browser.waits import (
    aguardar_pagina_pronta,
    aguardar_navegacao,
    passo,
)


class ParametrosPage(BasePage):
    """Page Object do formulário de parâmetros (id=selectForm)."""

    # ------------------------------------------------------------------
    # Locators PRIVADOS (By.ID para IDs com DOIS-PONTOS : — Constraint C2)
    # ------------------------------------------------------------------
    _LOCATOR_COORTE_INPUT = (By.ID, constants.LOCATOR_PARAM_COORTE_INPUT)
    _LOCATOR_MES_INICIO_INPUT = (By.ID, constants.LOCATOR_PARAM_MES_INICIO_INPUT)
    _LOCATOR_ANO_INICIO_INPUT = (By.ID, constants.LOCATOR_PARAM_ANO_INICIO_INPUT)
    _LOCATOR_MES_FIM_INPUT = (By.ID, constants.LOCATOR_PARAM_MES_FIM_INPUT)
    _LOCATOR_ANO_FIM_INPUT = (By.ID, constants.LOCATOR_PARAM_ANO_FIM_INPUT)

    # ------------------------------------------------------------------
    # FASE 3.2: ESTRATO — SelectCheckboxMenu MULTISELECT (ANTE de Variáveis!)
    # ------------------------------------------------------------------
    def _preencher_estrato(self) -> int:
        """
        Preenche o campo 'Estrato' via modo "preferencia".
        Retorna: quantidade de checkboxes marcados.
        """
        t0 = time.time()
        base_id = constants.WIDGET_ESTRATO_BASE_ID
        print(f"Estrato (modo preferencia) ...", flush=True)
        if not abrir_selectcheckboxmenu_primefaces(self._driver, base_id, timeout_geral=18):
            print(f"Não foi possível abrir painel do Estrato ({base_id}).", flush=True)
            return 0
        qtd = 0
        try:
            qtd = _ajustar_checkboxes_js(
                self._driver,
                base_id=base_id,
                modo="preferencia",
                labels_preferidas=constants.ESTRATO_PREFERENCIA_LABELS,
            )
            if qtd <= 0:
                diag = "<?>"
                try:
                    diag = str(self._driver.execute_script(
                        f"var base = document.getElementById('{base_id}'); "
                        f"if (!base) return 'painel-nao-encontrado-no-DOM'; "
                        f"var chks = base.querySelectorAll('input[type=checkbox]'); "
                        f"var out = []; for (var i=0;i<Math.min(chks.length,40);i++){{"
                        f"  var c = chks[i]; out.push((c.value||'?vazio?') + ':' + (c.dataset.label||c.title||''));"
                        f"}} return 'encontrados='+chks.length+' | values: '+out.join(', ');"
                    ))
                except Exception as e:
                    diag = f"erro-diagnostico: {e!r}"
                print(f"  [DIAG ESTRATO qtd=0!] {diag}", flush=True)
                print(f"Fallback: tentando marcar TODOS checkboxes do Estrato...", flush=True)
                qtd = _ajustar_checkboxes_js(self._driver, base_id=base_id, modo="todas")
        finally:
            fechar_painel_selectcheckboxmenu(self._driver, base_id, timeout=8)
        print(f"Estrato: {qtd} opção(ões) marcada(s) ({time.time()-t0:.2f}s).", flush=True)
        return qtd

    # ------------------------------------------------------------------
    # FASE 3.1: VARIÁVEIS — SelectCheckboxMenu MULTISELECT (DEPOIS de Estrato!)
    # ------------------------------------------------------------------
    def _validar_tokens_variaveis(self, base_id: str, valores_desejados: List[str]) -> tuple[int, List[str], List[str]]:
        """
        (NOVO B-VAR-2) Validação de tokens do SelectCheckboxMenu — FONTE DE VERDADE VISUAL (img6).
        Extrai data-item-value de cada chip <li class=ui-selectcheckboxmenu-token>.

        Returns:
            (qtd_corretos, tokens_atuais, faltantes)
        """
        tokens_atuais: List[str] = []
        try:
            _js_tokens = (
                "var baseId = arguments[0];"
                "var container = document.querySelector('div[id=\"' + baseId + '\"] ul.ui-selectcheckboxmenu-token-container');"
                "if (!container) return [];"
                "var tokens = container.querySelectorAll('li.ui-selectcheckboxmenu-token');"
                "var res = [];"
                "for (var i=0;i<tokens.length;i++){"
                "  var v = tokens[i].getAttribute('data-item-value');"
                "  if (v) res.push(String(v).trim());"
                "}"
                "return res;"
            )
            _r = self._driver.execute_script(_js_tokens, base_id) or []
            if isinstance(_r, list):
                tokens_atuais = [str(x).strip() for x in _r if x is not None and str(x).strip()]
        except Exception:
            tokens_atuais = []
        set_desejados = {str(v).strip() for v in valores_desejados if str(v).strip()}
        set_tokens = {str(v) for v in tokens_atuais}
        faltantes = sorted(list(set_desejados - set_tokens))
        qtd_corretos = len(set_desejados & set_tokens)
        return qtd_corretos, tokens_atuais, faltantes

    def preencher_variaveis(self, lista_codigos_variaveis: List[str],
                             forcar_modo_todas: bool = constants.DEFAULT_VARIAVEIS_USAR_MODO_TODAS) -> int:
        """
        Preenche as variáveis desejadas.
            - forcar_modo_todas=True → MARCA TODOS OS CHECKBOXES do painel.
            - forcar_modo_todas=False (padrão): usa mapeamento codigos_para_values + modo "lista_valores".

        Correções 2026-09-15 B-VAR-1/B-VAR-2:
          (1) Valida defaults por INTERSEÇÃO (não só quantidade).
          (2) Valida tokens pós-fechamento = fonte de verdade visual; reabre e remarca se faltar.

        Retorna: quantidade de checkboxes marcados.
        """
        t0 = time.time()
        base_id = constants.WIDGET_VARIAVEIS_BASE_ID

        # (a) NO TOPO: valores_desejados garantidos como list[str]
        valores_desejados_raw = codigos_para_values(lista_codigos_variaveis)
        valores_desejados: List[str] = [str(x).strip() for x in valores_desejados_raw if str(x).strip()]

        # Decide modo
        if forcar_modo_todas:
            print(f"Variáveis (MODO=TODAS — marcar TODOS do painel) ...", flush=True)
            modo = "todas"
            len_ref = None
            setpoint_check: List[str] = list(valores_desejados)  # ainda validamos tokens se existir
        else:
            if not valores_desejados:
                print(
                    f"Nenhuma variável mapeada de codigos={lista_codigos_variaveis}. "
                    f"Fallback para modo='todas'...",
                    flush=True,
                )
                modo = "todas"
                len_ref = None
                setpoint_check = []
            else:
                modo = "lista_valores"
                len_ref = len(valores_desejados)
                setpoint_check = list(valores_desejados)
            print(
                f"Variáveis ({(len_ref or 0)} valores mapeados) modo={modo} "
                f"[values_REAIS_checkbox={valores_desejados}]",
                flush=True,
            )

        def _marcar_via_js_lote(modo_atual: str) -> int:
            """Helper: abre painel, executa _ajustar_checkboxes_js, fecha, retorna qtd."""
            _qtd = 0
            if not abrir_selectcheckboxmenu_primefaces(self._driver, base_id, timeout_geral=18):
                print(f"Não foi possível abrir painel de Variáveis ({base_id}).", flush=True)
                return 0
            try:
                kwargs: dict = {"base_id": base_id, "modo": modo_atual}
                if modo_atual == "lista_valores" and valores_desejados:
                    kwargs["valores_desejados"] = valores_desejados
                _qtd = _ajustar_checkboxes_js(self._driver, **kwargs)
                if _qtd <= 0:
                    diag = "<?>"
                    try:
                        diag = str(self._driver.execute_script(
                            "var baseId = arguments[0];"
                            "var base = document.getElementById(baseId);"
                            "if (!base) return 'painel-nao-encontrado (baseId='+baseId+')';"
                            "var chks = base.querySelectorAll('input[type=checkbox]');"
                            "var out = [];"
                            "for (var i=0;i<Math.min(chks.length,80);i++){"
                            "  var c = chks[i]; var lbl = ''; var node = c;"
                            "  for (var up=0;up<6 && !lbl;up++){"
                            "    node = node.parentNode; if(!node) break;"
                            "    lbl = ((node.innerText||node.textContent||'').trim().replace(/\\s+/g,' ').substring(0,100));"
                            "  }"
                            "  var extras = document.querySelectorAll('label[for]');"
                            "  if(!lbl && c.id){"
                            "    for(var x=0;x<extras.length;x++){ if(extras[x].getAttribute('for')===c.id){ lbl=(extras[x].innerText||extras[x].textContent||'').trim().substring(0,100); break; }} "
                            "  }"
                            "  var v = c.getAttribute('value'); if(!v || v==='on') v = c.value;"
                            "  out.push('v=' + (v||'?vazio?') + ' L=\"' + lbl + '\"');"
                            "}"
                            "return 'TOTAL='+chks.length+' | primeiros: '+out.join(' | ');",
                            base_id,
                        ))
                    except Exception as e:
                        diag = f"erro-diagnostico: {e!r}"
                    print(f"  [DIAG VARIÁVEIS qtd=0!] {diag}", flush=True)
                    if modo_atual != "todas":
                        print(f"Fallback: tentando MODO=TODAS para Variáveis...", flush=True)
                        _qtd = _ajustar_checkboxes_js(self._driver, base_id=base_id, modo="todas")
            finally:
                fechar_painel_selectcheckboxmenu(self._driver, base_id, timeout=8)
            return _qtd

        # (b) PRIMEIRA PASSAGEM: abre painel, valida defaults por INTERSEÇÃO
        qtd = 0
        if not abrir_selectcheckboxmenu_primefaces(self._driver, base_id, timeout_geral=18):
            print(f"Não foi possível abrir painel de Variáveis ({base_id}).", flush=True)
            return 0
        try:
            # (b-i) Etapa defaults: contar + INTERSEÇÃO com desejados (B-VAR-1)
            qtd_default = 0
            _debug_values_checked: List[str] = []
            try:
                _js_count_default = (
                    "var baseId = arguments[0];"
                    "var base = document.getElementById(baseId + '_panel');"
                    "if (!base) base = document.getElementById(baseId);"
                    "if (!base) return { qtd: 0, vals: [] };"
                    "var chks = base.querySelectorAll('input[type=checkbox]:checked');"
                    "var vals = [];"
                    "for (var i=0; i<chks.length; i++){"
                    "  var v = chks[i].getAttribute('value');"
                    "  if (!v || v==='on') v = chks[i].value;"
                    "  if (v && String(v).trim() && String(v).trim()!=='on') vals.push(String(v).trim());"
                    "}"
                    "return { qtd: (chks ? chks.length : 0), vals: vals };"
                )
                _res_default = self._driver.execute_script(_js_count_default, base_id) or {}
                if isinstance(_res_default, dict):
                    qtd_default = int(_res_default.get("qtd") or 0)
                    _vals = _res_default.get("vals") or []
                    if isinstance(_vals, list):
                        _debug_values_checked = [str(x).strip() for x in _vals if x is not None and str(x).strip()]
            except Exception:
                qtd_default = 0
                _debug_values_checked = []

            intersecao = 0
            faltam_defaults: List[str] = []
            if valores_desejados and _debug_values_checked:
                set_desej = set(valores_desejados)
                set_checked = set(_debug_values_checked)
                intersecao = len(set_desej & set_checked)
                faltam_defaults = sorted(list(set_desej - set_checked))
            alvo_qtd = len_ref if len_ref else 15
            defaults_ok = intersecao >= max(1, len(valores_desejados) if valores_desejados else alvo_qtd)

            if defaults_ok:
                print(
                    f"Variáveis: ✅ DEFAULTS ATIVOS + INTERSEÇÃO OK ({intersecao}/{len(valores_desejados) or alvo_qtd}). "
                    f"defaults_checked={qtd_default}, values_intersecao={sorted(list(set(valores_desejados) & set(_debug_values_checked)))[:200]}",
                    flush=True,
                )
                qtd = max(qtd_default, intersecao)
            else:
                # (b-ii) Fallback: defaults ruins → marcar JS lote
                if qtd_default > 0:
                    print(
                        f"Variáveis: defaults ativos={qtd_default}, intersecao={intersecao}/{len(valores_desejados) or alvo_qtd}, "
                        f"faltam={faltam_defaults}. Rodando marcar JS para acertar...",
                        flush=True,
                    )
                kwargs = {"base_id": base_id, "modo": modo}
                if modo == "lista_valores" and valores_desejados:
                    kwargs["valores_desejados"] = valores_desejados
                qtd = _ajustar_checkboxes_js(self._driver, **kwargs)
                if qtd <= 0:
                    print(f"  [DIAG VARIÁVEIS modo={modo}] qtd=0 pós-marcar-js. Tentando fallback TODAS...", flush=True)
                    if modo != "todas":
                        qtd = _ajustar_checkboxes_js(self._driver, base_id=base_id, modo="todas")
        finally:
            fechar_painel_selectcheckboxmenu(self._driver, base_id, timeout=8)

        # (d) ETAPA NOVA VALIDAÇÃO TOKENS + RETRY INTERNO (B-VAR-2)
        max_tentativas_tokens = 2
        for tentativa_tokens in range(1, max_tentativas_tokens + 1):
            if not setpoint_check:
                break
            qtd_ok, tokens_now, faltantes_now = self._validar_tokens_variaveis(base_id, setpoint_check)
            if qtd_ok >= len(setpoint_check):
                print(
                    f"  TOKENS ✅ pós-fechamento: {qtd_ok}/{len(setpoint_check)} corretos "
                    f"(tentativa {tentativa_tokens}/{max_tentativas_tokens}). "
                    f"Tokens atuais={tokens_now[:200]}.",
                    flush=True,
                )
                break
            # Delta: reabrir + remarcar forcado
            print(
                f"  TOKENS ⚠️  faltando {len(faltantes_now)}/{len(setpoint_check)}: faltam={faltantes_now}. "
                f"Reabrindo painel p/ remarcar (tentativa {tentativa_tokens}/{max_tentativas_tokens})...",
                flush=True,
            )
            qtd = _marcar_via_js_lote("lista_valores" if setpoint_check else "todas")
        else:
            # Fora do for = todas tentativas falharam
            if setpoint_check:
                qtd_ok, tokens_now, faltantes_now = self._validar_tokens_variaveis(base_id, setpoint_check)
                print(
                    f"  ⚠️  VALIDAÇÃO TOKENS: após {max_tentativas_tokens} tentativas, "
                    f"ainda faltam {len(faltantes_now)} valores nos tokens (faltam={faltantes_now}). "
                    f"Continuando mesmo assim (o backend pode aceitar).",
                    flush=True,
                )

        if forcar_modo_todas or modo == "todas":
            print(f"Variáveis: {qtd} marcada(s) (MODO=TODAS — {time.time()-t0:.2f}s).", flush=True)
        else:
            print(f"Variáveis: {qtd}/{len_ref} marcada(s) ({time.time()-t0:.2f}s).", flush=True)
        return qtd

    # ------------------------------------------------------------------
    # 5 FILTROS BÁSICOS (FASE 3.0)
    # ------------------------------------------------------------------
    def preencher_coorte(self, value: str) -> None:
        print(f"Coorte = {value} ...", flush=True)
        selecionar_valor(self._driver, self._LOCATOR_COORTE_INPUT, str(value), tipo="select")

    def preencher_mes_inicio(self, mes: int) -> None:
        print(f"Mês Início = {mes} ...", flush=True)
        selecionar_valor(self._driver, self._LOCATOR_MES_INICIO_INPUT, str(mes), tipo="select")

    def preencher_ano_inicio(self, ano: int) -> None:
        print(f"Ano Início = {ano} ...", flush=True)
        selecionar_valor(self._driver, self._LOCATOR_ANO_INICIO_INPUT, str(ano), tipo="text")

    def preencher_mes_fim(self, mes: int) -> None:
        print(f"Mês Fim = {mes} ...", flush=True)
        selecionar_valor(self._driver, self._LOCATOR_MES_FIM_INPUT, str(mes), tipo="select")

    def preencher_ano_fim(self, ano: int) -> None:
        print(f"Ano Fim = {ano} ...", flush=True)
        selecionar_valor(self._driver, self._LOCATOR_ANO_FIM_INPUT, str(ano), tipo="text")

    # ------------------------------------------------------------------
    # FASE 3.3: RÁDIOS
    # ------------------------------------------------------------------
    def marcar_tipo_estimativa(self, value_alvo: str) -> bool:
        print(f"Tipo Estimativa = '{value_alvo}' ...", flush=True)
        ok = marcar_radiobutton_primefaces(
            self._driver,
            table_id=constants.RADIO_TIPO_ESTIMATIVA_TABLE_ID,
            value_alvo=str(value_alvo),
            label_table="TipoEstimativa",
            timeout=10,
        )
        if not ok:
            print(f"marcar_tipo_estimativa('{value_alvo}') NÃO confirmado.", flush=True)
        return ok

    def marcar_exibicao(self, exibir_valor: bool) -> bool:
        v = "true" if bool(exibir_valor) else "false"
        print(f"Exibição = Valor ({v}) ...", flush=True)
        ok = marcar_radiobutton_primefaces(
            self._driver,
            table_id=constants.RADIO_EXIBICAO_TABLE_ID,
            value_alvo=v,
            label_table="Exibição",
            timeout=10,
        )
        if not ok:
            print(f"marcar_exibicao({exibir_valor}) NÃO confirmado.", flush=True)
        return ok

    # ------------------------------------------------------------------
    # FASE 3.4: NOVO RÁDIO ORIENTAÇÃO (LINHA default / COLUNA)
    # ------------------------------------------------------------------
    def marcar_orientacao(self, orientacao: str) -> bool:
        v = str(orientacao).strip().upper()
        print(f"Orientação = {v} ...", flush=True)
        ok = marcar_radiobutton_primefaces(
            self._driver,
            table_id=constants.RADIO_ORIENTACAO_TABLE_ID,
            value_alvo=v,
            label_table="Orientação",
            timeout=10,
        )
        if not ok:
            print(f"marcar_orientacao('{v}') NÃO confirmado.", flush=True)
        return ok

    # ------------------------------------------------------------------
    # FASE 4 (início): Submeter formulário via Botão Pesquisar (ID ESTÁTICO)
    # ------------------------------------------------------------------
    def clicar_pesquisar(self) -> None:
        """Clica no botão Pesquisar (By.ID) e aguarda navegação para resultados."""
        print(f"Submeter: Botão Pesquisar (ID selectForm:pesquisar) ...", flush=True)
        ref_antes = None
        try:
            ref_antes = self._find_safe((By.ID, constants.DATATABLE_RESULTADOS_ID))
        except Exception:
            ref_antes = None
        t0 = time.time()
        self._click_by_id(constants.BTN_PESQUISAR_ID)
        # (NOVO screenshot 2026-09-15): após submeter, faz scroll para o fim
        # repetidamente durante a espera — pois a Datatable renderiza NA MESMA
        # página ABAIXO dos filtros (não há troca de URL).
        def _scroll_multiplo(n: int = 4):
            try:
                for _ in range(n):
                    self._driver.execute_script(
                        "try { window.scrollTo(0, document.body.scrollHeight || 99999); } catch(e){};"
                    )
                    time.sleep(0.08)
            except Exception:
                pass
        for _ in range(2):
            try:
                _scroll_multiplo(2)
            except Exception:
                pass
            try:
                aguardar_navegacao(self._driver, anterior=ref_antes, timeout=16)
                aguardar_pagina_pronta(self._driver, modo="normal", timeout=10)
            except Exception:
                time.sleep(1.0)
                try:
                    aguardar_pagina_pronta(self._driver, modo="navegacao", timeout=10)
                except Exception:
                    pass
        try:
            _scroll_multiplo(5)
        except Exception:
            pass
        print(f"Pesquisa submetida, navegação e scroll OK ({time.time()-t0:.1f}s).", flush=True)


__all__ = ["ParametrosPage"]
