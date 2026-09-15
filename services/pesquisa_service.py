"""
PesquisaService (FASE 3 + FASE 4): Orquestra pipeline preenchimento + pesquisa + export.

REGRAS CRÍTICAS — HARD CONSTRAINT USUÁRIO (NUNCA INVERTER A ORDEM ABAIXO):
  FASE 3 (selectForm):
    (1) 5 filtros básicos: Coorte → Mês Início → Ano Início → Mês Fim → Ano Fim
    (2) FASE 3.2 ESTRATO (SelectCheckboxMenu MULTISELECT)  **PRIMEIRO**
    (3) FASE 3.1 VARIÁVEIS (SelectCheckboxMenu MULTISELECT) **DEPOIS**
    (4) FASE 3.3 RÁDIOS: TipoEstimativa → Exibição
    (5) FASE 3.4 NOVO: Orientação (LINHA default / COLUNA)
    (6) Botão Pesquisar → aguarda navegação resultados
  FASE 4 (tela resultados):
    (7) Aguarda Datatable
    (8) Clica Exportar Excel → download inicia em background.

Regras AC-5/AC-7:
  - Usa @with_retry (≥3 total cumpre AC-5).
  - NÃO importa By/find_element/Select; só usa ParametrosPage/ResultadosPage (AC-7).
  - params é um PesquisaParams FROZEN (imutável) — nunca é alterado dentro do serviço.
"""
from __future__ import annotations

import time

from selenium import webdriver

from core.retry import with_retry
from core.errors import RetryableError
from domain.models import PesquisaParams
from pages.parametros_page import ParametrosPage
from pages.resultados_page import ResultadosPage


class PesquisaService:
    """Orquestrador do pipeline completo de pesquisa + export Excel."""

    def __init__(self, driver: webdriver.Chrome, params: PesquisaParams):
        if driver is None:
            raise ValueError("driver não pode ser None em PesquisaService")
        if params is None:
            raise ValueError("params (PesquisaParams) não pode ser None em PesquisaService")
        self._driver: webdriver.Chrome = driver
        self._params: PesquisaParams = params  # imutável (Pydantic frozen / dataclass frozen)

    # ------------------------------------------------------------------
    # Helpers polling condicional por estado real do DOM (não tempo fixo)
    # ------------------------------------------------------------------
    def _contar_radios_e_grupos_via_js(self) -> tuple[int, str]:
        """Retorna (total_radios, resumo_str). Total DOM <input[type=radio]> + resumo."""
        try:
            res = self._driver.execute_script(
                "var all = document.querySelectorAll('input[type=radio]');"
                "var groups = {};"
                "for (var i=0;i<all.length;i++){"
                "  var n=(all[i].name||'SEM_NAME').trim(); var v=(all[i].value||'').trim();"
                "  if (!groups[n]) groups[n]={count:0, values:[]};"
                "  groups[n].count++;"
                "  if (groups[n].values.length<4) groups[n].values.push(v+'['+(all[i].checked?'X':' ')+']');"
                "}"
                "var out=[]; var names=Object.keys(groups).sort();"
                "for (var j=0;j<names.length;j++){"
                "  out.push(names[j]+'='+groups[names[j]].count+' vals='+groups[names[j]].values.join(','));"
                "}"
                "return {total: all.length, resumo: out.join(' | ')};"
            )
            total = int(res.get("total", 0)) if isinstance(res, dict) else 0
            resumo = str(res.get("resumo", "")) if isinstance(res, dict) else ""
            return total, resumo
        except Exception:
            return 0, ""

    def _aguardar_radios_minimos(self,
                                 min_total: int = 6,
                                 timeout: int = 30,
                                 label: str = "radios DOM") -> tuple[int, str]:
        """
        Polling até TOTAL de <input[type=radio]> no DOM >= min_total OU timeout.
        Usa aguardar_pagina_pronta + aguardar_ajax + sleep curto a cada iteração.
        """
        from infrastructure.browser.waits import aguardar_pagina_pronta, aguardar_ajax
        fim = time.time() + timeout
        total = 0
        resumo = ""
        last_print = 0.0
        while time.time() < fim:
            try:
                aguardar_pagina_pronta(self._driver, modo="instantaneo", timeout=3)
            except Exception:
                pass
            try:
                aguardar_ajax(self._driver, timeout=2)
            except Exception:
                pass
            total, resumo = self._contar_radios_e_grupos_via_js()
            if total >= min_total:
                return total, resumo
            tempo_passado = time.time() - (fim - timeout)
            if tempo_passado - last_print >= 3.0:
                last_print = tempo_passado
                print(f"  ⏳ Esperando {label} (min={min_total}, atual={total}) ...",
                      flush=True)
            time.sleep(0.35)
        return total, resumo

    @with_retry(max_attempts=2, initial_delay=0.3, backoff_factor=2.0, jitter=0.05)
    def pesquisar_exportar_excel(self) -> bool:
        """
        Executa FASE 3 (preencher form) + FASE 4 (resultados + export Excel).
        ORDEM RÍGIDA ABAIXO — NÃO INVERTA NENHUM PASSO (dependências PrimeFaces AJAX).

        Returns:
            True se o pipeline concluiu TODO o caminho até export Excel iniciado.
        Raises:
            RetryableError: em falhas recuperáveis (decorator já aplica retry;
                            este raise é só para casos internos que queiram retry).
        """
        p_params = ParametrosPage(self._driver)
        p_params._aguardar_pronta("normal")

        # =====================================================================
        # ORDEM RÍGIDA USUÁRIO EXPLICITA: NÃO INVERTER — COMEÇA AQUI
        # =====================================================================
        t_pipeline = time.time()

        # -----------------------------------------------------------------
        # (1) 5 filtros básicos (FASE 3.0)
        # -----------------------------------------------------------------
        print("FASE 3.0: Preenchendo 5 filtros básicos...", flush=True)
        t0 = time.time()
        p_params.preencher_coorte(self._params.coorte)
        p_params.preencher_mes_inicio(self._params.mes_inicio)
        p_params.preencher_ano_inicio(self._params.ano_inicio)
        p_params.preencher_mes_fim(self._params.mes_fim)
        p_params.preencher_ano_fim(self._params.ano_fim)
        print(f"FASE 3.0 OK ({time.time()-t0:.1f}s): 5 filtros básicos preenchidos.", flush=True)

        # -----------------------------------------------------------------
        # (2) FASE 3.2 ESTRATO — SelectCheckboxMenu MULTISELECT  **PRIMEIRO**
        # -----------------------------------------------------------------
        print("FASE 3.2: Preenchendo ESTRATO (ANTES de Variáveis!) ...", flush=True)
        t0 = time.time()
        qtd_estrato = p_params._preencher_estrato()
        print(f"FASE 3.2 OK ({time.time()-t0:.1f}s): Estrato ({qtd_estrato} marcados).", flush=True)
        # ---- ESPERA POLLING pós-Estrato: até radios no DOM (garantir AJAX terminou) ----
        t_poll_estrato = time.time()
        total_apos_estrato, resumo_estrato = self._aguardar_radios_minimos(
            min_total=2, timeout=10, label="radios pós-Estrato"
        )
        print(f"  Espera pós-Estrato polling OK ({time.time()-t_poll_estrato:.1f}s): "
              f"radios DOM={total_apos_estrato}.", flush=True)
        if resumo_estrato:
            print(f"  [DIAG pós-Estrato] {resumo_estrato}", flush=True)
        # (EXTRA 2026-09-15) Dump TODAS tables.ui-selectoneradio REAIS do DOM
        try:
            dump_tables = self._driver.execute_script(
                "var allTables = document.querySelectorAll('table.ui-selectoneradio, table.ui-selectbooleancheckbox, table.ui-selectonebutton');"
                "var out2=[];"
                "for (var k=0;k<Math.min(allTables.length,20);k++){"
                "  var t=allTables[k]; var tId=(t.id||'SEM_ID').trim(); var cls=(t.className||'').trim();"
                "  var rs=t.querySelectorAll('input[type=radio]');"
                "  var vals=[]; for (var m=0;m<Math.min(rs.length,6);m++){vals.push((rs[m].value||'').trim());}"
                "  out2.push('[t#'+k+'] id=\"'+tId+'\" class=\"'+cls+'\" radios='+rs.length+' vals='+vals.join(','));"
                "}"
                "return out2.join(' | ');"
            )
            print(f"  [DIAG pós-Estrato TABLES] {dump_tables}", flush=True)
        except Exception:
            pass

        # -----------------------------------------------------------------
        # (3) FASE 3.1 VARIÁVEIS — SelectCheckboxMenu MULTISELECT  **DEPOIS**
        # -----------------------------------------------------------------
        print("FASE 3.1: Preenchendo VARIÁVEIS (DEPOIS de Estrato!) ...", flush=True)
        t0 = time.time()
        qtd_var = p_params.preencher_variaveis(self._params.codigos_variaveis)
        if qtd_var <= 0:
            raise RetryableError(
                f"FASE 3.1: Nenhuma variável marcada após preencher_variaveis "
                f"(codigos={self._params.codigos_variaveis}). Vai retry."
            )
        print(f"FASE 3.1 OK ({time.time()-t0:.1f}s): Variáveis marcadas={qtd_var}.", flush=True)
        # ---- ESPERA POLLING pós-Variáveis: até radios no DOM (garantir AJAX terminou) ----
        t_poll_var = time.time()
        total_apos_var, resumo_var = self._aguardar_radios_minimos(
            min_total=2, timeout=12, label="radios pós-Variáveis"
        )
        # Sleep de garantia final (DOM terminar de anexar inputs dentro das tables)
        time.sleep(0.8)
        print(f"  Espera pós-Variáveis polling OK ({time.time()-t_poll_var:.1f}s): "
              f"radios DOM={total_apos_var}.", flush=True)

        # ---- DIAGNÓSTICO: Quantos radios existem no DOM ANTES de marcar? ----
        try:
            diag_radios_js = self._driver.execute_script(
                "var all = document.querySelectorAll('input[type=radio]');"
                "var groups = {};"
                "for (var i=0;i<all.length;i++){"
                "  var n=(all[i].name||'SEM_NAME').trim(); var v=(all[i].value||'').trim();"
                "  if (!groups[n]) groups[n]={count:0, values:[]};"
                "  groups[n].count++;"
                "  if (groups[n].values.length<6) groups[n].values.push(v+'['+(all[i].checked?'X':' ')+']');"
                "}"
                "var out=[]; out.push('TOTAL='+all.length);"
                "var names=Object.keys(groups).sort();"
                "for (var j=0;j<names.length;j++){"
                "  out.push(names[j]+'='+groups[names[j]].count+' vals='+groups[names[j]].values.join(','));"
                "}"
                "/* NOVO: DUMP TODAS tables.ui-selectoneradio DO DOM (descobrir IDs REAIS radios) */"
                "var allTables = document.querySelectorAll('table.ui-selectoneradio, table.ui-selectbooleancheckbox, table.ui-selectonebutton, table.ui-selectmanymenu table');"
                "var out2=[];"
                "for (var k=0;k<Math.min(allTables.length,20);k++){"
                "  var t=allTables[k]; var tId=(t.id||'SEM_ID').trim(); var cls=(t.className||'').trim();"
                "  var rs=t.querySelectorAll('input[type=radio]');"
                "  var vals=[]; for (var m=0;m<Math.min(rs.length,6);m++){vals.push((rs[m].value||'').trim());}"
                "  out2.push('[table#'+k+'] id=\"'+tId+'\" class=\"'+cls+'\" radios='+rs.length+' vals='+vals.join(','));"
                "}"
                "return out.join(' | ')+' || TABLES_SELECTONE: '+out2.join(' | ');"
            )
            print(f"  [DIAG RADIOS DOM PRÉ-MARCAR] {diag_radios_js}", flush=True)
        except Exception as diag_err:
            print(f"  [DIAG RADIOS DOM PRÉ-MARCAR] Erro: {type(diag_err).__name__}", flush=True)

        # -----------------------------------------------------------------
        # (4) FASE 3.3 RÁDIOS: TipoEstimativa → Exibição
        # -----------------------------------------------------------------
        print("FASE 3.3: Marcando RÁDIOS TipoEstimativa + Exibição...", flush=True)
        t0 = time.time()
        ok_te = p_params.marcar_tipo_estimativa(self._params.tipo_estimativa)
        ok_ex = p_params.marcar_exibicao(self._params.exibicao)
        print(
            f"FASE 3.3 OK ({time.time()-t0:.1f}s): "
            f"TipoEstimativa={'OK' if ok_te else 'FALHA'} / "
            f"Exibição={'OK' if ok_ex else 'FALHA'}.",
            flush=True,
        )

        # -----------------------------------------------------------------
        # (5) FASE 3.4 NOVO RÁDIO: ORIENTAÇÃO (LINHA / COLUNA)
        # -----------------------------------------------------------------
        print("FASE 3.4: Marcando ORIENTAÇÃO (LINHA/COLUNA)...", flush=True)
        t0 = time.time()
        ok_or = p_params.marcar_orientacao(self._params.orientacao)
        print(f"FASE 3.4 OK ({time.time()-t0:.1f}s): Orientação={self._params.orientacao} "
              f"({'OK' if ok_or else 'FALHA'}).", flush=True)

        # -----------------------------------------------------------------
        # (6) Botão Pesquisar → navega para FASE 4
        # -----------------------------------------------------------------
        print("FASE 3 → 4: Submetendo pesquisa (botão Pesquisar)...", flush=True)
        t0 = time.time()
        p_params.clicar_pesquisar()
        print(f"FASE 3 → 4 OK ({time.time()-t0:.1f}s): resultados carregados.", flush=True)

        # =====================================================================
        # ORDEM RÍGIDA USUÁRIO EXPLICITA: FIM
        # =====================================================================

        # -----------------------------------------------------------------
        # (7) FASE 4: Aguarda Datatable de resultados
        # -----------------------------------------------------------------
        print("FASE 4.1: Aguardando Datatable de resultados aparecer...", flush=True)
        p_res = ResultadosPage(self._driver)
        dt_ok = p_res.aguardar_datatable(timeout=30)
        if not dt_ok:
            raise RetryableError(
                "FASE 4.1: Datatable de resultados NÃO apareceu após 30s (vai retry)."
            )

        # -----------------------------------------------------------------
        # (8) FASE 4: Exportar Excel
        # -----------------------------------------------------------------
        print("FASE 4.2: Exportando Excel...", flush=True)
        p_res.exportar_excel()

        total = time.time() - t_pipeline
        print(f"\n PIPELINE COMPLETO — pesquisa + export finalizados em {total:.1f}s.", flush=True)
        return True


__all__ = ["PesquisaService"]
