"""
ResultadosPage (POM): Tela de resultados FASE 4 — Datatable + Exportar Excel.

Locators são PRIVADOS (By.ID para IDs com dois-pontos `:` — Constraint C2).
Services não enxergam Selenium; só métodos alto-nível aguardar_datatable / exportar_excel.
"""
from __future__ import annotations

import time

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from config import constants
from infrastructure.browser.waits import aguardar_pagina_pronta, passo


class ResultadosPage(BasePage):
    """Page Object da tela de resultados (datatable + export Excel)."""

    _LOCATOR_DATATABLE = (By.ID, constants.DATATABLE_RESULTADOS_ID)
    _LOCATOR_EXPORT_EXCEL = (By.ID, constants.EXPORT_EXCEL_LINK_ID)

    # ------------------------------------------------------------------
    def aguardar_datatable(self, timeout: int = 50) -> bool:
        """
        Aguarda a datatable de resultados estar presente e visível.
        IMPORTANTE (screenshot 2026-09-15): a Datatable fica NA MESMA PÁGINA
        dos parâmetros (FASE 3), ABAIXO dos campos. Portanto é necessário
        fazer scroll até o final da página para visualizá-la.
        """
        print(f"Aguardando Datatable de resultados (timeout={timeout}s)...", flush=True)
        t0 = time.time()

        # SCROLL até o fim da página várias vezes durante a espera
        def _scroll_ate_fim():
            try:
                for _ in range(3):
                    self._driver.execute_script(
                        "try { window.scrollTo(0, document.body.scrollHeight || 99999); } catch(e){}"
                    )
                    time.sleep(0.06)
            except Exception:
                pass

        # (NOVO) Checar se FORM FASE 4 (listDifusaoLinhaForm) JÁ EXISTE
        # (isso prova que a pesquisa foi processada no servidor, mesmo que
        # a datatable ainda não esteja 100% renderizada)
        def _form_fase4_existe():
            try:
                form_id = constants.DATATABLE_RESULTADOS_ID.split(":")[0] + ":" + \
                          constants.DATATABLE_RESULTADOS_ID.split(":")[1] \
                    if ":" in constants.DATATABLE_RESULTADOS_ID else ""
                els = self._driver.find_elements(By.ID, "listDifusaoLinhaForm")
                if els:
                    try:
                        return bool(els[0].is_displayed() or els[0].get_attribute("id"))
                    except Exception:
                        return True
            except Exception:
                pass
            return False

        fim = time.time() + timeout
        ultima_exc = None
        while time.time() < fim:
            _scroll_ate_fim()
            # --- 1. Tentativa: presença DATATABLE direto ---
            try:
                el_dt = self._driver.find_elements(*self._LOCATOR_DATATABLE)
                if el_dt:
                    try:
                        if el_dt[0].is_displayed():
                            try:
                                aguardar_pagina_pronta(self._driver, modo="normal", timeout=5)
                            except Exception:
                                pass
                            print(f"Datatable pronta (por presença+visível, {time.time()-t0:.1f}s).", flush=True)
                            return True
                    except Exception:
                        pass
                    # Existe mas não está visível → ainda assim OK (pode estar offscreen)
                    try:
                        aguardar_pagina_pronta(self._driver, modo="normal", timeout=5)
                    except Exception:
                        pass
                    print(f"Datatable pronta (por presença no DOM, {time.time()-t0:.1f}s).", flush=True)
                    return True
            except Exception as e:
                ultima_exc = e

            # --- 2. Fallback: FORM FASE4 (listDifusaoLinhaForm) + datatable dentro ---
            try:
                if _form_fase4_existe():
                    forms = self._driver.find_elements(By.ID, "listDifusaoLinhaForm")
                    if forms:
                        dt_in = forms[0].find_elements(By.ID, constants.DATATABLE_RESULTADOS_ID)
                        if dt_in:
                            print(f"Datatable pronta (por form_fase4+datatable dentro, {time.time()-t0:.1f}s).", flush=True)
                            return True
            except Exception:
                pass

            # --- 3. Polling via WebDriverWait ---
            try:
                self._wait_presence(self._LOCATOR_DATATABLE, timeout=2)
                try:
                    self._wait_visible(self._LOCATOR_DATATABLE, timeout=2)
                except Exception:
                    pass
                print(f"Datatable pronta (WebDriverWait OK, {time.time()-t0:.1f}s).", flush=True)
                return True
            except Exception as e2:
                ultima_exc = e2
            time.sleep(0.25)

        # Timeout final → faz diagnóstico
        print(f"Datatable NÃO apareceu em {timeout}s: {ultima_exc!r}.", flush=True)
        try:
            import os
            caminho_ss = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "diag_sem_datatable.png")
            )
            _scroll_ate_fim()
            time.sleep(0.4)
            self._driver.save_screenshot(caminho_ss)
            print(f"  📸 [DIAG SEM DATATABLE] Screenshot (scroll+bottom) salvo: {caminho_ss}", flush=True)
        except Exception:
            print("  📸 [DIAG SEM DATATABLE] Screenshot falhou.", flush=True)
        try:
            dump_js = self._driver.execute_script(
                "var out = {}; "
                "out.url = document.location.href || ''; "
                "out.title = document.title || ''; "
                "var fm1 = document.getElementById('selectForm'); "
                "out.tem_selectForm = !!fm1; "
                "var fm2 = document.getElementById('listDifusaoLinhaForm'); "
                "out.tem_listDifusaoLinhaForm = !!fm2; "
                "if (fm2) { out.formFase4_tamanho = fm2.outerHTML.length; "
                "  var dt = fm2.querySelector('[id$=indicesVariavelDataTable]'); "
                "  out.tem_datatable_dentro_form4 = !!dt; "
                "  if (dt) out.datatable_classes = dt.className || ''; "
                "} "
                "var msgs = document.querySelectorAll('.ui-messages-detail, .ui-message-detail, .ui-growl-message span, div.message, div.erro, div.alert, span.rf-msg-det'); "
                "out.msgs = []; "
                "for (var i=0; i<msgs.length; i++){ var t=(msgs[i].innerText||msgs[i].textContent||'').trim(); if(t && t.length>2) out.msgs.push(t.substring(0,300)); } "
                "out.scrollY = window.scrollY || 0; "
                "out.body_altura = (document.body ? document.body.scrollHeight : -1); "
                "return out;"
            )
            if isinstance(dump_js, dict):
                print(f"  [DIAG SEM DATATABLE] URL={dump_js.get('url','?')}", flush=True)
                print(f"  [DIAG SEM DATATABLE] TITLE={dump_js.get('title','?')}", flush=True)
                print(f"  [DIAG SEM DATATABLE] tem_selectForm={dump_js.get('tem_selectForm')} | tem_listDifusaoLinhaForm={dump_js.get('tem_listDifusaoLinhaForm')} | form4_tam={dump_js.get('formFase4_tamanho')}", flush=True)
                print(f"  [DIAG SEM DATATABLE] tem_datatable_dentro_form4={dump_js.get('tem_datatable_dentro_form4')} | datatable_classes={dump_js.get('datatable_classes','')}", flush=True)
                print(f"  [DIAG SEM DATATABLE] scrollY={dump_js.get('scrollY')} | bodyAltura={dump_js.get('body_altura')}", flush=True)
                if dump_js.get("msgs") and isinstance(dump_js["msgs"], list):
                    print(f"  [DIAG SEM DATATABLE] MENSAGENS={str(dump_js['msgs'])[:2000]}", flush=True)
        except Exception as diag_e:
            print(f"  [DIAG SEM DATATABLE] Falhou JS dump: {diag_e!r}", flush=True)
        return False

    # ------------------------------------------------------------------
    def exportar_excel(self) -> str | None:
        """
        Clica no link de exportar Excel (By.ID) e aguarda início do download.
        Retorna None (download iniciado em background do Chrome).
        """
        print(f"Exportar Excel (ID {constants.EXPORT_EXCEL_LINK_ID}) ...", flush=True)
        t0 = time.time()
        try:
            self._click_by_id(constants.EXPORT_EXCEL_LINK_ID)
        except Exception as exc:
            print(f"Tentativa 1 exportar Excel (by-id) falhou: {exc!r}. Fallback JS selector.", flush=True)
            try:
                els = self._driver.find_elements(By.CSS_SELECTOR, constants.EXPORT_EXCEL_TITLE_SELECTOR)
                if els:
                    try:
                        self._driver.execute_script(
                            "try { arguments[0].click(); return true; } catch(e){ return false; }",
                            els[0],
                        )
                    except Exception:
                        try:
                            els[0].click()
                        except Exception:
                            raise
                else:
                    raise RuntimeError(f"Nenhum elemento encontrado para exportar Excel.")
            except Exception as e2:
                print(f"Exportar Excel falhou definitivamente: {e2!r}.", flush=True)
                return None
        time.sleep(2.2)
        print(f"Export Excel iniciado (~{time.time()-t0:.1f}s — Chrome baixando em background).", flush=True)
        return None


__all__ = ["ResultadosPage"]
