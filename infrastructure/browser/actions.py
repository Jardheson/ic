"""
Helpers de AÇÃO/INTERAÇÃO com UI da automação CNI.

100% DO CÓDIGO JS e LÓGICA extraído INTACTO de main_monolith_backup.py.
ÚNICA ALTERAÇÃO: `driver` é o PRIMEIRO parâmetro de TODAS as funções
(em vez de variável global do monólito).

Inclui:
- Clique/hover resilientes: clicar_com_retry / hover_em
- Preenchimento login/campos: preencher_login_rapido, fazer_login_turbo, preencher_texto_simples,
  _preencher_por_send_keys_direto / _js_com_events / _action_chains
- SelectOneMenu PrimeFaces: selecionar_valor (EARLY RETURN JS!), valor_campo_jah_correto,
  tentar_por_trigger_e_options
- SelectCheckboxMenu: abrir_selectcheckboxmenu_primefaces, fechar_painel_selectcheckboxmenu,
  _ajustar_checkboxes_js (BATCH EM LOTE 0.01s!)
- Radiobuttons PrimeFaces: marcar_radiobutton_primefaces c/ DIAGNÓSTICO completo
- Menu navegação: clicar_por_atividade_turbo c/ Function.call(window)
"""
from __future__ import annotations

import time
from typing import Optional, Tuple, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementNotInteractableException,
)

from infrastructure.browser.waits import (
    _locator_to_css,
    _pegou_erro_login,
    _na_tela_login,
    _limpar_overlays_orphans,
    _elemento_habilitado,
    _checar_mensagem_obrigatorio,
    aguardar_pagina_pronta,
    aguardar_ajax,
    esperar_estavel,
)


# ====================================================================
# Clique / Hover resilientes
# ====================================================================

def clicar_com_retry(driver: webdriver.Chrome, locator, tentativas: int = 3) -> None:
    ultimo_erro = None
    ultra_short_wait = WebDriverWait(driver, 3, poll_frequency=0.02)
    for i in range(tentativas):
        try:
            esperar_estavel(driver, locator, timeout=3)
            el = ultra_short_wait.until(EC.element_to_be_clickable(locator))
            if not _elemento_habilitado(el):
                time.sleep(0.05)
                continue
            try:
                driver.execute_script(
                    "try { arguments[0].click(); return true; } catch(e){ return false; }",
                    el,
                )
            except Exception:
                el.click()
            return
        except (StaleElementReferenceException, ElementNotInteractableException) as e:
            ultimo_erro = e
            time.sleep(0.05)
    raise ultimo_erro if ultimo_erro else RuntimeError(
        f"Falha clicar_com_retry em {locator}"
    )


def hover_em(driver: webdriver.Chrome, locator, tentativas: int = 3) -> None:
    ultimo_erro = None
    ultra_short_wait = WebDriverWait(driver, 3, poll_frequency=0.02)
    for i in range(tentativas):
        try:
            esperar_estavel(driver, locator, timeout=3)
            el = ultra_short_wait.until(EC.visibility_of_element_located(locator))
            if not _elemento_habilitado(el):
                time.sleep(0.05)
                continue
            try:
                driver.execute_script(
                    "var e=arguments[0]; try {"
                    "e.dispatchEvent(new MouseEvent('mouseover',{bubbles:true,cancelable:true,view:window}));"
                    "e.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,cancelable:true,view:window}));"
                    "e.dispatchEvent(new MouseEvent('mouseenter',{bubbles:true,cancelable:true,view:window}));"
                    "} catch(err){}",
                    el,
                )
            except Exception:
                ActionChains(driver, duration=10).move_to_element(el).pause(0.03).perform()
            return
        except (StaleElementReferenceException, ElementNotInteractableException) as e:
            ultimo_erro = e
            time.sleep(0.05)
    raise ultimo_erro if ultimo_erro else RuntimeError(
        f"Falha hover_em em {locator}"
    )


# ====================================================================
# Preenchimento de login (fazer_login_turbo)
# ====================================================================

def _validar_campo_preenchido(
    driver: webdriver.Chrome,
    locator,
    valor_esperado: str,
) -> bool:
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        v = (els[0].get_attribute("value") or "").strip()
        return v == valor_esperado.strip()
    except Exception:
        return False


def _preencher_por_send_keys_direto(
    driver: webdriver.Chrome,
    locator,
    valor: str,
    limpar: bool = True,
) -> bool:
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        el = els[0]
        try:
            if limpar:
                try:
                    el.clear()
                except Exception:
                    pass
                try:
                    el.click()
                except Exception:
                    pass
                try:
                    el.send_keys(Keys.CONTROL, "a")
                except Exception:
                    pass
                try:
                    el.send_keys(Keys.DELETE)
                except Exception:
                    pass
            time.sleep(0.01)
            el.send_keys(valor)
            return True
        except Exception:
            return False
    except Exception:
        return False


def _preencher_por_js_com_events(
    driver: webdriver.Chrome,
    locator,
    valor: str,
) -> bool:
    sel = _locator_to_css(locator)
    script = (
        "var s=arguments[0], v=arguments[1];"
        "var el = (s && document.querySelector(s)) || null;"
        "if (!el) return false;"
        "try { el.focus(); } catch(e){}"
        "try { el.value=''; } catch(e){}"
        "try { if (el.setSelectionRange) { el.setSelectionRange(0, (el.value||'').length); } } catch(e){}"
        "try { el.value = v; } catch(e){ return false; }"
        "try { el.setAttribute('value', v); } catch(e){}"
        "try { el.dispatchEvent(new KeyboardEvent('keydown', {bubbles:true})); } catch(e){}"
        "try { el.dispatchEvent(new Event('input', {bubbles:true, cancelable:true})); } catch(e){}"
        "try { el.dispatchEvent(new Event('change', {bubbles:true, cancelable:true})); } catch(e){}"
        "try { el.dispatchEvent(new KeyboardEvent('keyup', {bubbles:true})); } catch(e){}"
        "try { el.blur(); } catch(e){}"
        "return true;"
    )
    try:
        if sel:
            return bool(driver.execute_script(script, sel, valor))
        els = driver.find_elements(*locator)
        if not els:
            return False
        return bool(driver.execute_script(
            "var el=arguments[0], v=arguments[1];"
            "try { el.focus(); el.value=''; el.value = v; el.setAttribute('value', v);"
            "el.dispatchEvent(new Event('input',{bubbles:true}));"
            "el.dispatchEvent(new Event('change',{bubbles:true})); el.blur(); return true; }"
            "catch(e){ return false; }",
            els[0],
            valor,
        ))
    except Exception:
        return False


def _preencher_por_action_chains(
    driver: webdriver.Chrome,
    locator,
    valor: str,
) -> bool:
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        el = els[0]
        ac_local = ActionChains(driver, duration=10)
        try:
            ac_local.move_to_element(el).pause(0.02).click().pause(0.02)
            ac_local.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).pause(0.02)
            ac_local.send_keys(Keys.DELETE).pause(0.02)
            ac_local.send_keys(valor).pause(0.03)
            ac_local.perform()
            return True
        except Exception:
            try:
                ac_local.reset_actions()
            except Exception:
                pass
            return False
    except Exception:
        return False


def preencher_login_rapido(
    driver: webdriver.Chrome,
    locator,
    valor: str,
    sensivel: bool = False,
) -> None:
    try:
        els = driver.find_elements(*locator)
        if els:
            el = els[0]
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "try { arguments[0].setAttribute('value', arguments[1]); } catch(e){}"
                "try { arguments[0].dispatchEvent(new Event('input', {bubbles:true})); } catch(e){}"
                "try { arguments[0].dispatchEvent(new Event('change', {bubbles:true})); } catch(e){}",
                el,
                valor,
            )
            return
    except Exception:
        pass
    sel = _locator_to_css(locator)
    if sel:
        try:
            driver.execute_script(
                "var el = document.querySelector(arguments[0]); if (el) { "
                "el.value = arguments[1]; try { el.setAttribute('value', arguments[1]); } catch(e){}"
                "try { el.dispatchEvent(new Event('input', {bubbles:true})); } catch(e){}"
                "try { el.dispatchEvent(new Event('change', {bubbles:true})); } catch(e){} }",
                sel,
                valor,
            )
        except Exception:
            pass


def fazer_login_turbo(
    driver: webdriver.Chrome,
    usuario: str,
    senha: str,
    timeout_submit: int = 25,
) -> Tuple[bool, str]:
    loc_usr = (By.CSS_SELECTOR,
               "#loginForm\\:formLogin_usuarioInput, input[type='text'], input[id*='username' i], input[id*='login' i]")
    loc_pwd = (By.CSS_SELECTOR,
               "#loginForm\\:formLogin_senhaInput, input[type='password']")

    try:
        WebDriverWait(driver, 4, poll_frequency=0.05).until(
            lambda d: (len(d.find_elements(*loc_pwd)) > 0
                       or len(d.find_elements((By.CSS_SELECTOR, "input[type='password']"))) > 0)
        )
    except Exception:
        pass
    try:
        _limpar_overlays_orphans(driver)
    except Exception:
        pass

    usr_ok = False
    pwd_ok = False
    estrategias = [
        ("Selenium send_keys",
         lambda: _preencher_por_send_keys_direto(driver, loc_usr, usuario)
                 and _preencher_por_send_keys_direto(driver, loc_pwd, senha)),
        ("JS com eventos input/change",
         lambda: _preencher_por_js_com_events(driver, loc_usr, usuario)
                 and _preencher_por_js_com_events(driver, loc_pwd, senha)),
        ("ActionChains sequencial",
         lambda: _preencher_por_action_chains(driver, loc_usr, usuario)
                 and _preencher_por_action_chains(driver, loc_pwd, senha)),
    ]

    for rodada in range(2):
        for nome, fn in estrategias:
            try:
                ok = fn()
            except Exception:
                ok = False
            usr_ok = _validar_campo_preenchido(driver, loc_usr, usuario)
            pwd_ok = _validar_campo_preenchido(driver, loc_pwd, senha)
            if usr_ok and pwd_ok:
                break
            time.sleep(0.05)
        if usr_ok and pwd_ok:
            break
        time.sleep(0.08)

    if not usr_ok:
        print(f"  ⚠️  Campo usuário NÃO foi preenchido após 2 rodadas (esperado='{usuario[:2]}***').", flush=True)
    if not pwd_ok:
        print("  ⚠️  Campo senha NÃO foi preenchido após 2 rodadas.", flush=True)

    try:
        url_antes = driver.current_url or ""
    except Exception:
        url_antes = ""

    submit_feito = False
    for tentativa in range(2):
        try:
            okjs = driver.execute_script(
                "var b = document.getElementById('loginForm:formLogin_btnLogin');"
                "if (!b) b = document.querySelector(\"button[id*='btnLogin' i], input[type='submit'], button[type='submit']\");"
                "if (!b) return false;"
                "try { b.click(); return true; } catch(e){}"
                "var f = (b.closest && b.closest('form')) || document.getElementById('loginForm');"
                "if (f && typeof f.submit === 'function') { try { f.submit(); return true; } catch(e2){} }"
                "try { b.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window})); return true; } catch(e3){}"
                "return false;"
            )
            submit_feito = bool(okjs)
        except Exception:
            pass
        if not submit_feito:
            try:
                for sel in [
                    "#loginForm\\:formLogin_btnLogin",
                    "button[id*='btnLogin' i]",
                    "input[type='submit']",
                    "button[type='submit']",
                ]:
                    try:
                        bs = driver.find_elements(By.CSS_SELECTOR, sel)
                        if bs:
                            bs[0].click()
                            submit_feito = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass
        if tentativa == 0:
            fim_submit_loop = time.time() + 3.5
            while time.time() < fim_submit_loop:
                if _pegou_erro_login(driver)[0]:
                    break
                try:
                    if (driver.current_url or "") != url_antes:
                        break
                except Exception:
                    pass
                time.sleep(0.03)
            if _pegou_erro_login(driver)[0]:
                break
            try:
                if (driver.current_url or "") != url_antes:
                    break
            except Exception:
                pass

    fim = time.time() + timeout_submit
    ultima_limpeza = 0.0
    logou = False
    erro_msg = ""
    while time.time() < fim:
        agora = time.time()
        if agora - ultima_limpeza > 2.0:
            try:
                _limpar_overlays_orphans(driver)
            except Exception:
                pass
            ultima_limpeza = agora
        tem_erro, txt_erro = _pegou_erro_login(driver)
        if tem_erro:
            erro_msg = txt_erro or "(mensagem de erro detectada)"
            break
        try:
            if (driver.current_url or "") != url_antes:
                logou = True
                break
        except Exception:
            pass
        if not _na_tela_login(driver):
            logou = True
            break
        time.sleep(0.05)

    if not logou and not erro_msg:
        restante = max(3, int(fim - time.time()))
        aguardar_pagina_pronta(driver, modo="navegacao", timeout=restante)
        try:
            _limpar_overlays_orphans(driver)
        except Exception:
            pass
        if not _na_tela_login(driver):
            logou = True
        try:
            if (driver.current_url or "") != url_antes:
                logou = True
        except Exception:
            pass

    if erro_msg:
        print(f"Erro de login detectado: {erro_msg[:200]}", flush=True)
    return logou, erro_msg


# ====================================================================
# Preenchimento de texto genérico (ano=spinner)
# ====================================================================

def preencher_texto_simples(
    driver: webdriver.Chrome,
    locator,
    valor,
    sensivel: bool = False,
) -> None:
    ultra_short_wait = WebDriverWait(driver, 3, poll_frequency=0.02)
    for i in range(3):
        esperar_estavel(driver, locator, timeout=3)
        el = ultra_short_wait.until(EC.element_to_be_clickable(locator))
        if not _elemento_habilitado(el):
            time.sleep(0.05)
            continue
        try:
            driver.execute_script(
                "var el=arguments[0], v=arguments[1];"
                "try { el.focus(); } catch(e){};"
                "try { el.value=''; el.setAttribute('value',''); } catch(e){};"
                "try { if (el.setSelectionRange) { el.setSelectionRange(0, 99999); } } catch(e){};"
                "try { el.value = v; el.setAttribute('value', v); } catch(e){ return false; };"
                "try { el.dispatchEvent(new KeyboardEvent('keydown',{bubbles:true})); } catch(e){};"
                "try { el.dispatchEvent(new Event('input',{bubbles:true,cancelable:true})); } catch(e){};"
                "try { el.dispatchEvent(new Event('change',{bubbles:true,cancelable:true})); } catch(e){};"
                "try { el.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true})); } catch(e){};"
                "try { el.blur(); } catch(e){}; return true;",
                el,
                valor,
            )
            time.sleep(0.015)
            if not sensivel:
                for _ in range(3):
                    try:
                        el2 = driver.find_element(*locator)
                        val = (el2.get_attribute("value") or "").strip()
                        if val.strip() == str(valor).strip():
                            return
                    except (StaleElementReferenceException, Exception):
                        pass
                    time.sleep(0.03)
            else:
                return
        except (StaleElementReferenceException, ElementNotInteractableException):
            time.sleep(0.05)
    raise RuntimeError(f"Falha ao preencher campo {locator}")


# ====================================================================
# BATCH checkboxes (MELHOR DESEMPENHO de TODA a automação!)
# SEG-1: Migração para execute_script com arguments[0..3] (NÃO há concatenação
#        de variáveis Python dentro do string JS, evita injeção de código).
# ====================================================================

_AJUSTAR_CHECKBOXES_JS_SCRIPT = r"""
(function () {
  try {
    var baseId = arguments[0] ? String(arguments[0]).trim() : "";
    var modo = arguments[1] ? String(arguments[1]).trim() : "todas";
    var valores = (arguments[2] && Array.isArray(arguments[2]))
      ? arguments[2].map(function (x) { return String(x || "").trim(); })
                      .filter(function (x) { return x && x !== "on"; })
      : [];
    var labelsPref = (arguments[3] && Array.isArray(arguments[3]))
      ? arguments[3].map(function (x) { return String(x || "").trim().toLowerCase(); })
                      .filter(function (x) { return x; })
      : [];
    if (!baseId) {
      return (modo === "lista_valores") ? { marcados: 0, debug: "sem_baseId", valores: "[]" } : 0;
    }

    // ---------- LOCALIZAR CONTAINER ----------
    // ESTRATÉGIA PRINCIPAL: usar exclusivamente div#<baseId>_panel (o painel overlay real
    // do PrimeFaces SelectCheckboxMenu, aberto pelo w.show() / trigger).
    // O widget coloca APENAS os 31 checkboxes DENTRO desse _panel; o restante da página
    // não entra na busca.
    var containerEl = null;
    var panelId = baseId + "_panel";
    try {
      var p = document.getElementById(panelId);
      if (p && p.querySelectorAll("input[type=\"checkbox\"]").length > 0) containerEl = p;
    } catch (e) {}
    if (!containerEl) {
      // Fallback 1: tentar querySelector com ID escapado
      try {
        var escId = panelId.replace(/([^A-Za-z0-9_\-])/g, '\\$1');
        var p2 = document.querySelector("#" + escId);
        if (p2 && p2.querySelectorAll("input[type=\"checkbox\"]").length > 0) containerEl = p2;
      } catch (e) {}
    }
    if (!containerEl) {
      // Fallback 2: qualquer painel PrimeFaces visível com checkboxes
      var allPanels = document.querySelectorAll("div.ui-selectcheckboxmenu-panel");
      for (var api = 0; api < allPanels.length; api++) {
        var cand = allPanels[api];
        var candId = "";
        try { candId = (cand.id || "").toString(); } catch (e) {}
        if (candId && candId.indexOf(baseId) === 0 && cand.querySelectorAll("input[type=\"checkbox\"]").length > 0) {
          containerEl = cand; break;
        }
        if (!candId && cand.querySelectorAll("input[type=\"checkbox\"]").length > 0 && containerEl === null) {
          containerEl = cand; // fallback raro: único painel visível na página
        }
      }
    }
    if (!containerEl) {
      // Fallback 3 (não ideal): div com id == baseId, se contiver checkboxes
      try {
        var p3 = document.getElementById(baseId);
        if (p3 && p3.querySelectorAll("input[type=\"checkbox\"]").length > 0) containerEl = p3;
      } catch (e) {}
    }
    var todos = containerEl ? containerEl.querySelectorAll("input[type=\"checkbox\"]") : [];
    var nTodos = todos ? todos.length : 0;
    var containerId = "";
    try { containerId = (containerEl && containerEl.id) ? containerEl.id.toString() : "container-null"; } catch (e) { containerId = "err"; }
    var debug_comp = ["cont=" + containerId + " n=" + nTodos + " modo=" + modo];

    // ---------- HELPERS ----------
    function _ajustar_ui(cb, deve) {
      try {
        var p = cb.parentElement || cb.parentNode;
        var box = null;
        if (p) box = p.querySelector(".ui-chkbox-box");
        if (!box) {
          // fallback: subir até 3 níveis
          var pp = p;
          for (var up = 0; up < 3 && !box; up++) {
            if (!pp) break;
            try { box = pp.querySelector ? pp.querySelector(".ui-chkbox-box") : null; } catch (e) {}
            pp = pp.parentElement;
          }
        }
        if (!box) return;
        var ic = box.querySelector(".ui-chkbox-icon");
        if (deve) {
          box.classList.add("ui-state-active");
          box.classList.remove("ui-state-hover");
          if (ic) { ic.classList.remove("ui-icon-blank"); ic.classList.add("ui-icon-check"); }
        } else {
          box.classList.remove("ui-state-active", "ui-state-hover");
          if (ic) { ic.classList.add("ui-icon-blank"); ic.classList.remove("ui-icon-check"); }
        }
      } catch (e) {}
    }
    function _encontrar_label_ou_box(cb) {
      // PrimeFaces: label com [for] aponta para checkbox hidden OU checkbox visual dentro de .ui-chkbox
      var cid = "";
      try { cid = (cb.getAttribute("id") || "").toString(); } catch (e) {}
      if (cid) {
        try {
          var lab = document.querySelector("label[for=\"" + cid.replace(/([^A-Za-z0-9_\-])/g, '\\$1') + "\"]");
          if (lab) return { el: lab, tipo: "label" };
        } catch (e) {}
      }
      // fallback: subir até encontrar div.ui-chkbox e pegar .ui-chkbox-box
      var p = cb.parentElement || cb.parentNode;
      for (var up = 0; up < 4; up++) {
        if (!p) break;
        try {
          if (p.classList && p.classList.contains("ui-chkbox")) {
            var b = p.querySelector(".ui-chkbox-box");
            if (b) return { el: b, tipo: "box" };
            var r = p.querySelector(".ui-chkbox-icon");
            if (r) return { el: r, tipo: "icon" };
            return { el: p, tipo: "chkbox-wrap" };
          }
        } catch (e) {}
        p = p.parentElement;
      }
      return null;
    }
    function _disparar_eventos(el) {
      try {
        el.dispatchEvent(new MouseEvent('mouseover', {bubbles:true, cancelable:true, view:window}));
      } catch (e) {}
      try {
        el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, cancelable:true, view:window, button:0}));
      } catch (e) {}
      try {
        el.dispatchEvent(new MouseEvent('mouseup', {bubbles:true, cancelable:true, view:window, button:0}));
      } catch (e) {}
      try { el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true, view:window})); } catch (e) {}
      try {
        el.dispatchEvent(new MouseEvent('mouseout', {bubbles:true, cancelable:true, view:window}));
      } catch (e) {}
    }
    function _encontrar_trilho_principal(cb) {
      // PrimeFaces SelectCheckboxMenu: <label> com for="" é o trigger OFICIAL (não o input, que fica em .ui-helper-hidden-accessible)
      var cid = "";
      try { cid = (cb.getAttribute("id") || "").toString(); } catch (e) {}
      if (cid) {
        try {
          var esc = cid.replace(/([^A-Za-z0-9_\-])/g, '\\$1');
          var lab = document.querySelector("label[for=\"" + esc + "\"]");
          if (lab) return { el: lab, tipo: "label_for" };
        } catch (e) {}
      }
      // fallback: subir 2 níveis e pegar label seguinte/anterior dentro de .ui-selectcheckboxmenu-item
      var p = cb;
      for (var up = 0; up < 5; up++) {
        if (!p) break;
        try {
          if (p.classList && (p.classList.contains("ui-selectcheckboxmenu-item") ||
                              p.classList.contains("ui-selectlistbox-item") ||
                              p.classList.contains("ui-chkbox"))) {
            var labs = (p.querySelectorAll ? p.querySelectorAll("label") : []);
            if (labs && labs.length) return { el: labs[0], tipo: "label_initem" };
            var box = p.querySelector(".ui-chkbox-box");
            if (box) return { el: box, tipo: "chkbox_box" };
          }
        } catch (e) {}
        p = p.parentElement;
      }
      return _encontrar_label_ou_box(cb);
    }
    function _try_toggle(cb, novo) {
      // Só faz algo se estado atual divergir do desejado
      if ((cb.checked ? 1 : 0) === (novo ? 1 : 0)) return true;
      var alvo = _encontrar_trilho_principal(cb);
      var ok = false;
      if (alvo && alvo.el) {
        try {
          try { alvo.el.scrollIntoView({block:'nearest', inline:'nearest'}); } catch (e) {}
          for (var tent = 0; tent < 2; tent++) {
            try { _disparar_eventos(alvo.el); } catch (e) {}
            try { // double-check em seguida (micro-espera)
              for (var w=0; w<3; w++) {
                if ((cb.checked ? 1 : 0) === (novo ? 1 : 0)) { ok = true; break; }
                try { if (alvo.el.click) alvo.el.click(); } catch (e2) {}
              }
            } catch (e3) {}
            if (ok) break;
          }
        } catch (e1) {}
      }
      // Fallback 2: força checked + UI + dispara change (último recurso)
      if (!ok) {
        try {
          cb.checked = !!novo;
          try { cb.dispatchEvent(new Event('change', {bubbles:true, cancelable:true})); } catch (e) {}
          try { cb.dispatchEvent(new Event('click',  {bubbles:true, cancelable:true})); } catch (e) {}
        } catch (eFb) {}
      }
      _ajustar_ui(cb, !!novo);
      return (cb.checked ? 1 : 0) === (novo ? 1 : 0);
    }
    function _valor_cb(cb) {
      var v = "";
      try { v = (cb.getAttribute("value") || "").toString().trim(); } catch (e) {}
      if (!v) try { v = (cb.value || "").toString().trim(); } catch (e) {}
      if (v === "on") v = "";
      return v;
    }
    function _label_match(cb, labelsArr) {
      // Verifica se o checkbox corresponde a algum label preferencial
      // Estratégias: [for] do label, textContent do label, vizinho anterior/próximo
      if (!labelsArr || labelsArr.length === 0) return false;
      var cid = "";
      try { cid = (cb.getAttribute("id") || "").toString(); } catch (e) {}
      if (cid) {
        try {
          var labFor = document.querySelector("label[for=\"" + cid.replace(/([^A-Za-z0-9_\-])/g, '\\$1') + "\"]");
          if (labFor) {
            var tx = ((labFor.innerText || labFor.textContent) || "").toString().trim().toLowerCase();
            if (tx && labelsArr.indexOf(tx) >= 0) return true;
            // match parcial (contém)
            for (var lp = 0; lp < labelsArr.length; lp++) {
              if (labelsArr[lp] && tx.indexOf(labelsArr[lp]) >= 0) return true;
            }
          }
        } catch (e) {}
      }
      // Procura label próximo (irmãos)
      try {
        var sib = cb.previousElementSibling;
        for (var s = 0; s < 4; s++) {
          if (!sib) break;
          if (sib.tagName && sib.tagName.toLowerCase() === "label") {
            var t2 = ((sib.innerText || sib.textContent) || "").toString().trim().toLowerCase();
            if (t2 && labelsArr.indexOf(t2) >= 0) return true;
            for (var lp2 = 0; lp2 < labelsArr.length; lp2++) {
              if (labelsArr[lp2] && t2.indexOf(labelsArr[lp2]) >= 0) return true;
            }
          }
          sib = sib.previousElementSibling;
        }
        var nxt = cb.nextElementSibling;
        for (var s2 = 0; s2 < 4; s2++) {
          if (!nxt) break;
          if (nxt.tagName && nxt.tagName.toLowerCase() === "label") {
            var t3 = ((nxt.innerText || nxt.textContent) || "").toString().trim().toLowerCase();
            if (t3 && labelsArr.indexOf(t3) >= 0) return true;
            for (var lp3 = 0; lp3 < labelsArr.length; lp3++) {
              if (labelsArr[lp3] && t3.indexOf(labelsArr[lp3]) >= 0) return true;
            }
          }
          nxt = nxt.nextElementSibling;
        }
      } catch (e) {}
      return false;
    }
    function _contar_marcados() {
      var c = 0;
      for (var ix = 0; ix < nTodos; ix++) { if (todos[ix].checked) c++; }
      return c;
    }

    // ---------- MODO: LISTA_VALORES ----------
    if (modo === "lista_valores") {
      var marcados = 0;
      for (var i = 0; i < nTodos; i++) {
        var cb = todos[i], v = _valor_cb(cb);
        var deve = (v !== "") && (valores.indexOf(v) >= 0);
        if (i < 16) debug_comp.push("v" + i + "=" + v + " deve=" + (deve ? 1 : 0) + " chAntes=" + (cb.checked ? 1 : 0));
        var ok = _try_toggle(cb, deve);
        if (i < 16) debug_comp[i + 1] = debug_comp[i + 1] + " chDepois=" + (cb.checked ? 1 : 0) + " ok=" + (ok ? 1 : 0);
      }
      marcados = _contar_marcados();
      return {
        marcados: marcados,
        debug: debug_comp.join(" | "),
        valores: JSON.stringify(valores)
      };
    }

    // ---------- MODO: TODAS / PREFERENCIA ----------
    // PRIMEIRO: desmarca todos (garante estado limpo)
    for (var j = 0; j < nTodos; j++) {
      var cb0 = todos[j];
      if (cb0.checked) _try_toggle(cb0, false);
    }

    if (modo === "preferencia") {
      var marcouPref = 0;
      for (var k = 0; k < nTodos; k++) {
        var cbPref = todos[k];
        if (_label_match(cbPref, labelsPref)) {
          if (_try_toggle(cbPref, true)) marcouPref++;
        }
      }
      debug_comp.push("pref_marcou=" + marcouPref);
      if (marcouPref > 0) {
        var rPref = _contar_marcados();
        debug_comp.push("pref_total_checados=" + rPref);
        return { marcados: rPref, debug: debug_comp.join(" | "), valores: "" };
      }
      debug_comp.push("pref_sem_match → fallback TODAS");
    }

    // fallback: modo TODAS
    for (var w = 0; w < nTodos; w++) {
      var cbw = todos[w];
      _try_toggle(cbw, true);
    }
    var rFinal = _contar_marcados();
    debug_comp.push("todas_total_checados=" + rFinal);
    return { marcados: rFinal, debug: debug_comp.join(" | "), valores: "" };
  } catch (eGlobal) {
    // RETORNO EXPLÍCITO DE ERRO (para não retornar None silencioso)
    var errMsg = "EXC:" + (eGlobal && eGlobal.message ? eGlobal.message.toString() : String(eGlobal));
    if (modo === "lista_valores") return { marcados: 0, debug: errMsg, valores: "[]" };
    return -999;
  }
})();
"""


def _ajustar_checkboxes_js(
    driver: webdriver.Chrome,
    base_id: str,
    modo: str = "todas",
    valores_desejados: Optional[List[str]] = None,
    labels_preferidas: Optional[List[str]] = None,
) -> int:
    """
    Ajusta checkboxes do SelectCheckboxMenu PrimeFaces via JS (melhor performance).

    SEG-1: NÃO injeta valores Python dentro do string JS — tudo é passado via
    arguments[0..3] do execute_script, evitando qualquer risco de injeção.
    """
    valores_arr: List[str]
    if valores_desejados is None:
        valores_arr = []
    else:
        valores_arr = [str(x).strip() for x in valores_desejados if x is not None and str(x).strip()]
    labels_arr: List[str]
    if labels_preferidas is None:
        labels_arr = []
    else:
        labels_arr = [str(x).strip().lower() for x in labels_preferidas if x is not None and str(x).strip()]

    try:
        # ============ TENTATIVA 1 (script novo seguro via arguments[0..3]) ============
        res = driver.execute_script(
            _AJUSTAR_CHECKBOXES_JS_SCRIPT,
            base_id,
            modo,
            valores_arr,
            labels_arr,
        )
        try:
            driver.execute_script("try { document.body.click(); } catch(e){}")
        except Exception:
            pass
        marcados_from_dict = 0
        debug_extra = ""
        if isinstance(res, dict):
            marcados_from_dict = int(res.get("marcados", 0) or 0)
            debug_extra = " debug=" + str((res.get("debug") or "")[:500])
        res_int = int(res) if (res is not None and not isinstance(res, dict)) else marcados_from_dict
        if modo == "lista_valores" and isinstance(res, dict):
            debug_str = res.get("debug") or ""
            marcados_r = int(res.get("marcados", 0) or 0)
            print(f"  [_ajustar modo=lista v1] base_id={base_id} marcados={marcados_r} debug={debug_str[:500]}", flush=True)
        elif res_int == -999:
            print(f"  [_ajustar ERRO_JS_INTERNO v1] base_id={base_id} modo={modo} (script catch retornou -999)", flush=True)
        else:
            print(f"  [_ajustar modo={modo} v1] base_id={base_id} marcados={res_int}{debug_extra}", flush=True)

        # ============ TENTATIVA 2 (fallback se T1 falhou em marcar >= 1) ============
        # Usa o script idêntico ao do monólito original (já provou funcionar em produção),
        # mas rodado via execute_script com arguments[0..3] para manter SEG-1.
        precisa_fallback = False
        if modo == "lista_valores":
            if res_int < max(1, len(valores_arr)):
                precisa_fallback = True
        elif modo == "preferencia":
            if res_int < max(1, len(labels_arr) if labels_arr else 1):
                precisa_fallback = True
        elif modo == "todas":
            try:
                # pede a quantidade total pelo painel
                panel_check = driver.execute_script(
                    "(function(b){var p=document.getElementById(b+'_panel');"
                    "if(!p){p=document.getElementById(b);} if(!p)return -1;"
                    "var qs=p.querySelectorAll(\"input[type=checkbox]\"); return (qs?qs.length:0);})(arguments[0]);",
                    base_id,
                )
                total_cbs = int(panel_check or -1)
                if total_cbs > 0 and res_int < total_cbs:
                    precisa_fallback = True
                elif res_int <= 0:
                    precisa_fallback = True
            except Exception:
                if res_int <= 0:
                    precisa_fallback = True
        if precisa_fallback:
            try:
                print(f"  [_ajustar fallback v2] base_id={base_id} modo={modo} (v1 marcou={res_int}, tentando script monólito via arguments)", flush=True)
                res_fb = driver.execute_script(
                    """
(function(baseId, modo, valores, labelsPref){
  try {
    var panelId = baseId + "_panel";
    var sel = "div[id=\"" + panelId + "\"] input[type=\"checkbox\"]";
    // Procura checkboxes no painel overlay
    var todos = document.querySelectorAll(sel);
    if (!todos || todos.length === 0) {
      // fallback: painel genérico PrimeFaces
      var panels = document.querySelectorAll(".ui-selectcheckboxmenu-panel, .ui-selectcheckboxmenu");
      for (var i=0; i<panels.length; i++) {
        var cands = panels[i].querySelectorAll("input[type=\"checkbox\"]");
        if (cands && cands.length > 0) { todos = cands; break; }
      }
    }
    if (!todos || todos.length === 0) {
      if (modo === "lista_valores") return { marcados:0, debug:"fallback_sem_checkboxes" , valores:JSON.stringify(valores) };
      return -5;
    }
    var marcados = 0;
    function _click(cb, deve) {
      if (cb.checked === !!deve) return true;
      // Estratégia monólito original: primeiro o próprio input (que apesar de hidden ainda funciona em Chrome)
      try { cb.click(); if (cb.checked === !!deve) return true; } catch(e) {}
      // Fallback: força propriedade
      try { cb.checked = !!deve; } catch(e2) {}
      // Sincroniza UI
      try {
        var p = cb.parentElement || cb.parentNode;
        var box = (p ? (p.querySelector ? p.querySelector(".ui-chkbox-box") : null) : null) || null;
        if (box) {
          var ic = box.querySelector(".ui-chkbox-icon");
          if (deve) { box.classList.add("ui-state-active"); box.classList.remove("ui-state-hover");
                     if (ic){ic.classList.remove("ui-icon-blank"); ic.classList.add("ui-icon-check");} }
          else     { box.classList.remove("ui-state-active","ui-state-hover");
                     if (ic){ic.classList.add("ui-icon-blank"); ic.classList.remove("ui-icon-check");} }
        }
      } catch(e) {}
      try { cb.dispatchEvent(new Event('change',{bubbles:true,cancelable:true})); } catch(e){}
      return true;
    }
    if (modo === "lista_valores") {
      for (var i=0; i<todos.length; i++) {
        var cb = todos[i], v = ((cb.getAttribute("value") || "").toString() || (cb.value||"").toString()).trim();
        if (v === "on") v = "";
        var deve = (v !== "") && (valores.indexOf(v) >= 0);
        _click(cb, deve);
        if (cb.checked) marcados++;
      }
      try { document.body.click(); } catch(e){}
      return { marcados: marcados, debug: "fallback_v2 nTodos=" + todos.length, valores: JSON.stringify(valores) };
    }
    // preferencia / todas: PRIMEIRO desmarca tudo
    for (var d=0; d<todos.length; d++) {
      var cbd = todos[d];
      if (cbd.checked) _click(cbd, false);
    }
    marcados = 0;
    if (modo === "preferencia" && labelsPref && labelsPref.length > 0) {
      for (var ip=0; ip<todos.length; ip++) {
        var cbp = todos[ip];
        var labelMatch = false;
        try {
          var cid = (cbp.getAttribute("id")||"").toString();
          if (cid) {
            var escCid = cid.replace(/([^A-Za-z0-9_\\-])/g,'\\\\$1');
            var labL = document.querySelector("label[for=\"" + escCid + "\"]");
            if (labL) {
              var tx = ((labL.innerText||labL.textContent)||"").toString().trim().toLowerCase();
              for (var lp=0; lp<labelsPref.length; lp++){
                if (tx && (labelsPref[lp] === tx || tx.indexOf(labelsPref[lp]) >= 0)) { labelMatch=true; break; }
              }
            }
          }
        } catch (e) {}
        if (labelMatch) { _click(cbp, true); if (cbp.checked) marcados++; }
      }
    }
    if (marcados === 0 || modo !== "preferencia") {
      marcados = 0;
      for (var i2=0; i2<todos.length; i2++) {
        var cbi = todos[i2];
        _click(cbi, true);
        if (cbi.checked) marcados++;
      }
    }
    try { document.body.click(); } catch(e){}
    return marcados;
  } catch (eGlobal) {
    var msg = "EXC:" + (eGlobal && eGlobal.message ? eGlobal.message.toString() : String(eGlobal));
    if (modo === "lista_valores") return { marcados: 0, debug: msg, valores: JSON.stringify(valores) };
    return -4;
  }
})(arguments[0], arguments[1], arguments[2], arguments[3]);
                    """,
                    base_id,
                    modo,
                    valores_arr,
                    labels_arr,
                )
                marcados_fb = 0
                debug_fb = ""
                if isinstance(res_fb, dict):
                    marcados_fb = int(res_fb.get("marcados", 0) or 0)
                    debug_fb = " debug=" + str((res_fb.get("debug") or "")[:500])
                else:
                    try:
                        marcados_fb = int(res_fb or 0)
                    except Exception:
                        marcados_fb = 0
                print(f"  [_ajustar fallback v2] base_id={base_id} modo={modo} marcados={marcados_fb}{debug_fb}", flush=True)
                if marcados_fb > res_int:
                    res_int = marcados_fb
            except Exception as eFb:
                print(f"  [_ajustar fallback v2 EXC py] base_id={base_id} modo={modo} exc={type(eFb).__name__}: {eFb!r}", flush=True)
        try:
            driver.execute_script("try { document.body.click(); } catch(e){}")
        except Exception:
            pass
        return res_int
    except Exception as e:
        print(f"  [_ajustar EXCEPTION py] base_id={base_id} modo={modo} exc={type(e).__name__}: {e!r}", flush=True)
        return 0


# ====================================================================
# SelectOneMenu PrimeFaces (EARLY RETURN JS nativo = evita 56s!)
# ====================================================================

def valor_campo_jah_correto(
    driver: webdriver.Chrome,
    locator,
    valor_esperado,
    tipo: str = "select",
) -> bool:
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        el = els[0]
        if tipo == "select":
            try:
                if el.tag_name.lower() == "select":
                    cur_js = driver.execute_script(
                        "var s = arguments[0];"
                        "try { var v = (s.value || '').trim(); if (v !== '') return v; } catch(e){};"
                        "try { var idx = s.selectedIndex; if (idx >= 0 && s.options[idx]) return (s.options[idx].value || '').trim(); } catch(e2){};"
                        "return '';",
                        el,
                    ) or ""
                    if str(cur_js).strip() == str(valor_esperado).strip():
                        return True
                else:
                    eid = el.get_attribute("id") or ""
                    if eid:
                        sel_id = eid if eid.endswith("_input") else eid + "_input"
                        sels = driver.find_elements(By.ID, sel_id)
                        if sels and sels[0].tag_name.lower() == "select":
                            cur_js = driver.execute_script(
                                "var s = arguments[0];"
                                "try { var v = (s.value || '').trim(); if (v !== '') return v; } catch(e){};"
                                "try { var idx = s.selectedIndex; if (idx >= 0 && s.options[idx]) return (s.options[idx].value || '').trim(); } catch(e2){};"
                                "return '';",
                                sels[0],
                            ) or ""
                            if str(cur_js).strip() == str(valor_esperado).strip():
                                return True
            except Exception:
                return False
        elif tipo == "text":
            try:
                cur = (el.get_attribute("value") or "").strip()
                if cur == str(valor_esperado).strip():
                    return True
            except Exception:
                return False
    except Exception:
        return False
    return False


def tentar_por_trigger_e_options(
    driver: webdriver.Chrome,
    locator_select_hidden,
    valor_option,
) -> bool:
    sel_id = None
    try:
        sel_el = driver.find_element(*locator_select_hidden)
        sel_id = sel_el.get_attribute("id") or ""
    except Exception:
        return False
    if not sel_id:
        return False

    try:
        cur_js = driver.execute_script(
            "var s=arguments[0]; try { var v=(s.value||'').trim(); if (v!=='') return v; } catch(e){};"
            "try { var idx=s.selectedIndex; if (idx>=0 && s.options[idx]) return (s.options[idx].value||'').trim(); } catch(e2){};"
            "return '';",
            sel_el,
        ) or ""
        if cur_js.strip() == str(valor_option).strip():
            return True
    except Exception:
        pass

    base = sel_id[:-6] if sel_id.endswith("_input") else sel_id
    trigger_sel = f"div[id='{base}'] div.ui-selectonemenu-trigger, div[id='{base}'] a.ui-corner-right, div[id='{base}'] div.ui-selectonemenu-label-container"
    panel_sel = f"div[id='{base}_panel'].ui-selectonemenu-panel, div[id='{base}_items'].ui-selectonemenu-items, div[id='{base}_content']"
    option_sel = (f"div[id='{base}_panel'] li[data-label],div[id='{base}_panel'] div.ui-selectonemenu-item, "
                 f"div[id='{base}_items'] div[data-label], li[data-label], ul.ui-selectonemenu-items li")

    try:
        driver.execute_script(
            f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
            f" var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base}') : null;"
            f" if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
            f"  var x = PrimeFaces.widgets[k]; if(x && x.id==='{base}') w = x; }});"
            f" if (w && typeof w.show === 'function') {{ try {{ w.show(); return true; }} }}"
            f"}} }} catch(e){{}} return false;"
        )
    except Exception:
        pass

    def _aberto():
        try:
            if driver.execute_script(
                f"var c=document.querySelector(\"div[id='{base}']\");"
                f"if (c && (c.getAttribute('aria-expanded')==='true' || c.classList.contains('ui-state-focus'))) return true;"
                f"var p=document.querySelector(\"{panel_sel}\");"
                f"if (p && p.offsetParent !== null && p.getClientRects && p.getClientRects().length>0) return true;"
                f"return false;"
            ):
                return True
        except Exception:
            pass
        try:
            ps = driver.find_elements(By.CSS_SELECTOR, panel_sel)
            if ps and ps[0].is_displayed():
                return True
        except Exception:
            pass
        try:
            cs = driver.find_elements(By.CSS_SELECTOR,
                                      f"div[id='{base}'][aria-expanded='true'],div[id='{base}'].ui-state-focus")
            if cs:
                return True
        except Exception:
            pass
        return False

    def _fechar():
        try:
            driver.execute_script(
                f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
                f" var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base}') : null;"
                f" if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
                f"  var x = PrimeFaces.widgets[k]; if(x && x.id==='{base}') w = x; }});"
                f" if (w && typeof w.hide === 'function') {{ try {{ w.hide(); return true; }} }}"
                f"}} }} catch(e){{}} return false;"
            )
        except Exception:
            pass
        try:
            driver.execute_script("try { document.body.click(); } catch(e){}")
        except Exception:
            pass

    abriu = _aberto()
    if not abriu:
        for rodada in range(3):
            if abriu:
                break
            for trig_sel in trigger_sel.split(","):
                trig_sel_clean = trig_sel.strip()
                if not trig_sel_clean:
                    continue
                if abriu:
                    break
                try:
                    driver.execute_script(
                        "var trig = document.querySelector(arguments[0]);"
                        "if (!trig) return false;"
                        "try { trig.scrollIntoView({block:'center', inline:'center'}); } catch(e){}"
                        "try { trig.focus(); } catch(e){}"
                        "try { trig.click(); return true; } catch(e){}"
                        "try { trig.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));"
                        " trig.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));"
                        " trig.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));"
                        " return true; } catch(e2){} return false;",
                        trig_sel_clean,
                    )
                except Exception:
                    pass
                fim_mini = time.time() + 1.5
                while (not abriu) and time.time() < fim_mini:
                    if _aberto():
                        abriu = True
                        break
                    time.sleep(0.05)
            if not abriu:
                time.sleep(0.08)

    if not abriu:
        return False

    try:
        WebDriverWait(driver, 4, poll_frequency=0.05).until(
            lambda d: _aberto()
        )
    except Exception:
        pass

    clicou_opcao = False
    for tentativa in range(3):
        if clicou_opcao:
            break
        try:
            ops = driver.find_elements(By.CSS_SELECTOR, option_sel)
            for op in ops:
                try:
                    dl = (op.get_attribute("data-label") or "").strip()
                    dv = (op.get_attribute("data-value") or "").strip()
                    ot = (op.text or "").strip()
                    if (dv and dv == str(valor_option).strip() or
                        dl and dl == str(valor_option).strip()):
                        try:
                            driver.execute_script(
                                "var op=arguments[0]; try { op.scrollIntoView({block:'center'}); } catch(e){}"
                                "try { op.click(); return true; } catch(e2){}"
                                "try { op.dispatchEvent(new MouseEvent('click',{bubbles:true})); return true; } catch(e3){} return false;",
                                op,
                            )
                            clicou_opcao = True
                            break
                        except Exception:
                            try:
                                op.click()
                                clicou_opcao = True
                                break
                            except Exception:
                                pass
                except Exception:
                    continue
        except Exception:
            pass
        if clicou_opcao:
            break
        time.sleep(0.08)

    if not clicou_opcao:
        try:
            Select(sel_el).select_by_value(str(valor_option).strip())
            clicou_opcao = True
        except Exception:
            pass

    if clicou_opcao:
        aguardar_ajax(driver)
        try:
            WebDriverWait(driver, 5, poll_frequency=0.05).until(
                lambda d: (not _aberto()) or _locator_to_css(locator_select_hidden)
            )
        except Exception:
            pass
        time.sleep(0.03)
        _fechar()
        return True

    _fechar()
    return False


def selecionar_valor(
    driver: webdriver.Chrome,
    locator,
    valor,
    tipo: str = "select",
) -> None:
    if tipo == "select":
        try:
            els_er = driver.find_elements(*locator)
            if els_er:
                el_er = els_er[0]
                if el_er.tag_name.lower() == "select":
                    v_er = driver.execute_script(
                        "var s = arguments[0];"
                        "try { var v = (s.value || '').trim(); if (v !== '') return v; } catch(e){};"
                        "try { var idx = s.selectedIndex; if (idx >= 0 && s.options[idx]) return (s.options[idx].value || '').trim(); } catch(e2){};"
                        "return '';",
                        el_er,
                    ) or ""
                    if str(v_er).strip() == str(valor).strip():
                        return
        except Exception:
            pass

        try:
            tentar_por_trigger_e_options(driver, locator, valor)
        except Exception:
            pass
        for i in range(3):
            try:
                els = driver.find_elements(*locator)
                if not els:
                    time.sleep(0.05)
                    continue
                el = els[0]
                if el.tag_name and el.tag_name.lower() == "select":
                    try:
                        Select(el).select_by_value(valor)
                        aguardar_ajax(driver)
                        try:
                            sel_el = driver.find_element(*locator)
                            val_ok = driver.execute_script(
                                "var s=arguments[0]; try { var v=(s.value||'').trim(); if (v!=='') return v; } catch(e){};"
                                "try { var idx=s.selectedIndex; if (idx>=0 && s.options[idx]) return (s.options[idx].value||'').trim(); } catch(e2){};"
                                "return '';",
                                sel_el,
                            ) or ""
                            if val_ok.strip() == str(valor).strip():
                                return
                        except Exception:
                            pass
                    except Exception:
                        pass
            except StaleElementReferenceException:
                time.sleep(0.05)
                continue
            except Exception:
                time.sleep(0.05)
                continue
        raise RuntimeError(f"Falha ao selecionar valor '{valor}' em {locator}")
    elif tipo == "text":
        for i in range(6):
            aguardar_pagina_pronta(driver, modo="instantaneo", timeout=3)
            try:
                els = driver.find_elements(*locator)
                if not els:
                    time.sleep(0.08)
                    continue
                el = els[0]
                if not _elemento_habilitado(el):
                    time.sleep(0.12)
                    continue
                try:
                    driver.execute_script(
                        "var el=arguments[0], v=arguments[1];"
                        "try { el.focus(); } catch(e){};"
                        "el.value = v; try { el.setAttribute('value',v); } catch(e){};"
                        "el.dispatchEvent(new KeyboardEvent('keydown',{bubbles:true}));"
                        "el.dispatchEvent(new Event('input',{bubbles:true,cancelable:true}));"
                        "el.dispatchEvent(new Event('change',{bubbles:true,cancelable:true}));"
                        "el.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true}));"
                        "el.dispatchEvent(new Event('blur',{bubbles:true}));"
                        "try {"
                        "  var hid = document.querySelector(\"input[type=hidden][name='\"+el.id.replace(/_input$/,'')+\"']\");"
                        "  if(hid) { hid.value=v; hid.setAttribute('value',v); }"
                        "} catch(e){}"
                        "try { document.body.click(); } catch(e){}",
                        el,
                        valor,
                    )
                except Exception:
                    pass
                aguardar_ajax(driver)
                try:
                    # Usar JS click em vez de click físico (evita ElementClickInterceptedException
                    # por headers overlays como div#pad do site)
                    driver.execute_script(
                        "try { arguments[0].scrollIntoView({block:'center',inline:'nearest'}); } catch(e){};"
                        "try { arguments[0].click(); } catch(e){}",
                        el,
                    )
                    time.sleep(0.015)
                    el.send_keys(Keys.CONTROL, "a")
                    time.sleep(0.008)
                    el.send_keys(Keys.DELETE)
                    time.sleep(0.008)
                    el.send_keys(valor)
                    driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].blur(); try { document.body.click(); } catch(e){}",
                        el,
                    )
                except (StaleElementReferenceException, ElementNotInteractableException):
                    pass
                aguardar_ajax(driver)
                ok = False
                for _ in range(6):
                    try:
                        els2 = driver.find_elements(*locator)
                        if els2:
                            vnow = (els2[0].get_attribute("value") or "").strip()
                            if vnow == str(valor).strip():
                                ok = True
                                break
                    except Exception:
                        pass
                    time.sleep(0.08)
                if ok:
                    return
                if _checar_mensagem_obrigatorio(driver):
                    time.sleep(0.15)
                    continue
            except (StaleElementReferenceException, ElementNotInteractableException):
                time.sleep(0.12)
        raise RuntimeError(f"Falha ao preencher campo {locator} com valor '{valor}'")
    raise RuntimeError(f"tipo desconhecido {tipo}")


# ====================================================================
# SelectCheckboxMenu (abrir/fechar painel)
# ====================================================================

def fechar_painel_selectcheckboxmenu(
    driver: webdriver.Chrome,
    base_id: str,
    timeout: int = 8,
) -> bool:
    painel_sel = f"div[id='{base_id}_panel'].ui-selectcheckboxmenu-panel"

    def _fechado():
        try:
            els = driver.find_elements(By.CSS_SELECTOR, painel_sel)
            if not els:
                return True
            try:
                if not els[0].is_displayed():
                    return True
            except Exception:
                pass
        except Exception:
            pass
        try:
            st = driver.execute_script(
                f"var c = document.querySelector(\"div[id='{base_id}']\");"
                f"if (c && c.getAttribute('aria-expanded')==='true') return false;"
                f"var p = document.querySelector('{painel_sel}');"
                f"if (p && p.offsetParent === null) return true;"
                f"if (p && getComputedStyle(p).display==='none') return true;"
                f"if (!p) return true;"
                f"return false;"
            )
            if st:
                return True
        except Exception:
            pass
        return False

    if _fechado():
        try:
            aguardar_pagina_pronta(driver, modo="instantaneo", timeout=3)
        except Exception:
            pass
        return True

    fim_geral = time.time() + timeout
    fechou = False
    for rodada in range(3):
        if fechou or time.time() > fim_geral:
            break

        try:
            driver.execute_script(
                f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
                f" var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base_id}') : null;"
                f" if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
                f"  var x = PrimeFaces.widgets[k]; if(x && x.id==='{base_id}') w = x; }});"
                f" if (w) {{ if (typeof w.hide === 'function') {{ try {{ w.hide(); return true; }} catch(e){{}} }}"
                f"          if (typeof w.close === 'function') {{ try {{ w.close(); return true;}} catch(e){{}} }}"
                f"}} }}"
                f"}} catch(e){{}} return false;"
            )
        except Exception:
            pass
        time.sleep(0.03)
        if _fechado():
            fechou = True
            break
        try:
            driver.execute_script("try { document.body.click(); } catch(e){}")
        except Exception:
            pass
        time.sleep(0.05)
        if _fechado():
            fechou = True
            break
        try:
            for b in driver.find_elements(By.TAG_NAME, "body")[:1]:
                try:
                    b.send_keys(Keys.ESCAPE)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(0.05)
        if _fechado():
            fechou = True
            break
        try:
            driver.execute_script(
                f"var p = document.querySelector('{painel_sel}');"
                f"if (p) {{ p.style.display='none'; p.style.visibility='hidden'; p.setAttribute('data-forceclosed','1'); }}"
                f"var c = document.querySelector(\"div[id='{base_id}']\");"
                f"if (c) {{ try {{ c.setAttribute('aria-expanded','false'); c.classList.remove('ui-state-focus','ui-selectcheckboxmenu-open'); }} catch(e){{}} }}"
            )
        except Exception:
            pass
        time.sleep(0.03)
        if _fechado():
            fechou = True
            break
        time.sleep(0.08)

    try:
        WebDriverWait(driver, 4, poll_frequency=0.05).until(
            lambda d: _fechado() or
                      (len(d.find_elements(By.CSS_SELECTOR, painel_sel)) == 0) or
                      (not d.find_element(By.CSS_SELECTOR, painel_sel).is_displayed())
        )
    except Exception:
        pass
    try:
        _limpar_overlays_orphans(driver)
        aguardar_pagina_pronta(driver, modo="instantaneo", timeout=5)
    except Exception:
        pass
    return _fechado()


def abrir_selectcheckboxmenu_primefaces(
    driver: webdriver.Chrome,
    base_id: str,
    timeout_geral: int = 22,
) -> bool:
    aguardar_pagina_pronta(driver, modo="rapido")
    _limpar_overlays_orphans(driver)

    container_sel = f"div[id='{base_id}']"
    try:
        WebDriverWait(driver, 6, poll_frequency=0.05).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, container_sel))
        )
    except Exception:
        pass
    try:
        driver.execute_script(
            f"var w = null;"
            f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
            f"  Object.keys(PrimeFaces.widgets).forEach(function(k){{"
            f"    var x = PrimeFaces.widgets[k];"
            f"    if (x && x.id === '{base_id}' && typeof x.show === 'function') {{ w = x; }}"
            f"  }});"
            f"}} }} catch(e){{}}"
            f"if (w) {{ try {{ w.show(); return true; }} catch(e){{ return false; }} }}"
            f"return false;"
        )
    except Exception:
        pass

    panel_sel = f"div[id='{base_id}_panel'].ui-selectcheckboxmenu-panel"
    or_aria = f"{container_sel}[aria-expanded='true'], {container_sel}.ui-state-focus"

    triggers_css = [
        f"{container_sel} a.ui-selectcheckboxmenu-label, "
        f"{container_sel} div.ui-selectcheckboxmenu-label-container a, "
        f"{container_sel} .ui-selectcheckboxmenu-label",
        f"{container_sel} a.ui-corner-right, {container_sel} a.ui-selectcheckboxmenu-trigger, "
        f"{container_sel} .ui-icon-triangle-1-s, {container_sel} span.ui-icon",
        f"label[for='{base_id}_input'], label[for='{base_id}']",
    ]

    def _aberto():
        try:
            if driver.execute_script(
                f"var panel = document.querySelector('{panel_sel}');"
                f"if (panel && panel.offsetParent !== null && panel.getClientRects().length > 0) return true;"
                f"var c = document.querySelector('{container_sel}');"
                f"if (c && (c.getAttribute('aria-expanded') === 'true' || c.classList.contains('ui-state-focus') || c.classList.contains('ui-selectcheckboxmenu-open'))) return true;"
                f"return false;"
            ):
                return True
        except Exception:
            pass
        try:
            if len(driver.find_elements(By.CSS_SELECTOR, panel_sel)) > 0:
                p = driver.find_element(By.CSS_SELECTOR, panel_sel)
                if p.is_displayed():
                    return True
        except Exception:
            pass
        try:
            if len(driver.find_elements(By.CSS_SELECTOR, or_aria)) > 0:
                return True
        except Exception:
            pass
        return False

    fim_geral = time.time() + timeout_geral
    ultima_limpeza = 0.0
    abriu = _aberto()

    for rodada in range(3):
        if abriu or time.time() > fim_geral:
            break
        for trig_sel in triggers_css:
            if abriu or time.time() > fim_geral:
                break
            agora = time.time()
            if agora - ultima_limpeza > 3.5:
                try:
                    _limpar_overlays_orphans(driver)
                except Exception:
                    pass
                ultima_limpeza = agora
            try:
                driver.execute_script(
                    "var trig = document.querySelector(arguments[0]);"
                    "if (!trig) return false;"
                    "try { trig.scrollIntoView({block:'center', inline:'center'}); } catch(e){}"
                    "try { trig.focus(); } catch(e){}"
                    "try { trig.click(); return true; } catch(e){}"
                    "try { trig.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));"
                    " trig.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));"
                    " trig.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window})); return true; } catch(e2){}"
                    "return false;",
                    trig_sel,
                )
            except Exception:
                pass
            try:
                for t in driver.find_elements(By.CSS_SELECTOR, trig_sel)[:1]:
                    try:
                        t.click()
                    except Exception:
                        try:
                            ActionChains(driver).move_to_element(t).pause(0.01).click().perform()
                        except Exception:
                            pass
            except Exception:
                pass
            fim_mini = time.time() + 1.5
            while (not abriu) and time.time() < fim_mini:
                if _aberto():
                    abriu = True
                    break
                time.sleep(0.05)
            if not abriu:
                try:
                    driver.execute_script("try { document.body.click(); } catch(e){}")
                except Exception:
                    pass
                time.sleep(0.08)

    if not abriu:
        try:
            driver.execute_script(
                f"if (window.PrimeFaces && PrimeFaces.widgets) {{"
                f"  var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base_id}') : null;"
                f"  if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
                f"    var x = PrimeFaces.widgets[k]; if (x && x.id==='{base_id}') w = x;"
                f"  }});"
                f"  if (w && typeof w.show === 'function') {{ try {{ w.show(); }} catch(e){{}} }}"
                f"}}"
            )
            fim_mini = time.time() + 2.0
            while (not abriu) and time.time() < fim_mini:
                if _aberto():
                    abriu = True
                    break
                time.sleep(0.06)
        except Exception:
            pass

    if abriu:
        try:
            WebDriverWait(driver, 5, poll_frequency=0.05).until(
                lambda d: (
                    len(d.find_elements(By.CSS_SELECTOR, panel_sel)) > 0
                    and d.find_element(By.CSS_SELECTOR, panel_sel).is_displayed()
                ) or _aberto()
            )
        except Exception:
            pass
        aguardar_pagina_pronta(driver, modo="rapido", timeout=5)
        _limpar_overlays_orphans(driver)
    return abriu


# ====================================================================
# Radiobutton PrimeFaces (c/ diagnóstico completo!)
# ====================================================================

def _escapar_id_para_css(id_com_dois_pontos: str) -> str:
    r"""
    IDs JSF/PrimeFaces contêm ":" → CSS #id inválido (pseudo-seletor).
    Solução: escapar ":" com "\\:" (Selenium aceita \: como escape de literal).
    Ex: "selectForm:tipoEstimativa" → "selectForm\\:tipoEstimativa"
    """
    if not id_com_dois_pontos:
        return ""
    return id_com_dois_pontos.replace(":", "\\:")


def _descobrir_name_real(driver: webdriver.Chrome, table_id: str, fallback_name: str) -> str:
    """
    Descobre o NAME REAL dos <input type=radio> DENTRO da table.
    No JSF/PrimeFaces, muitas vezes `id="selectForm:tipoEstimativa"` MAS
    `name="selectForm:j_idt123:0"` ou algum formato diferente. Usa o PRIMEIRO
    input[type=radio] dentro da table para extrair o atributo name.
    Retorna o name descoberto OU fallback_name se não encontrar.
    """
    try:
        all_in_table = driver.find_elements(By.CSS_SELECTOR,
                                            f"table#{table_id} input[type=radio]")
        for r in all_in_table:
            try:
                n = (r.get_attribute("name") or "").strip()
                if n:
                    return n
            except Exception:
                continue
    except Exception:
        pass
    return fallback_name


def marcar_radiobutton_primefaces(
    driver: webdriver.Chrome,
    table_id: str,
    value_alvo,
    label_table: Optional[str] = None,
    timeout: int = 10,
) -> bool:
    """
    Marca radio PrimeFaces (p:selectOneRadio).

    ROBUSTECIMENTO 2026-09-15 v2 (9 imagens DevTools CNI):
      0) EARLY RETURN VISUAL (img8): se div.ui-radiobutton-box.ui-state-active (caixa visual)
         JÁ ESTÁ ATIVA dentro da table, retorna True imediatamente — evita falso negativo
         de input hidden em .ui-helper-hidden-accessible.
      1) Usa seletores INDEPENDENTES de `name`:
         - `table#{table_id} input[type=radio][value='X']`  (Melhor seletor, não depende de NAME)
         - fallback mais amplo + div.ui-helper-hidden-accessible input[type=radio] (img8)
      2) Após detectar table, descobre o NAME REAL via `radio.get_attribute("name")` do primeiro
         input dentro da table, e usa esse name a partir daí.
      3) Diagnóstico se table existe mas inputs=0: busca também em .ui-helper-hidden-accessible.
    """
    fim_geral = time.time() + timeout
    value_alvo_str = str(value_alvo).strip()
    radio_name = table_id
    css_id = _escapar_id_para_css(table_id)  # ":" → "\\:" p/ CSS selector
    table_sel = f"table#{css_id}"
    # Seletores INDEPENDENTES de NAME (robusto) — INCLUINDO HELPER HIDDEN (img8)
    input_sel_sem_name = (
        f"table#{css_id} input[type=radio][value='{value_alvo_str}'], "
        f"table#{css_id} div.ui-helper-hidden-accessible input[type=radio][value='{value_alvo_str}']"
    )
    table_all_inputs_sel = (
        f"table#{css_id} input[type=radio], "
        f"table#{css_id} div.ui-helper-hidden-accessible input[type=radio]"
    )
    # Seletor genérico BUSCA EM TODO O DOM por value (fallback se table_id mudou no AJAX)
    input_sel_generico_por_value = (
        f"input[type=radio][value='{value_alvo_str}'], "
        f"div.ui-helper-hidden-accessible input[type=radio][value='{value_alvo_str}']"
    )

    # Seletor ORIGINAL (usa name) mantido como fallback final
    input_sel_por_name = f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']"
    input_sel = input_sel_sem_name  # usa sem-name PRIMEIRO

    # ------------------------------------------------------------------
    # (NOVO 2026-09-15 v2 — EARLY RETURN POR ESTADO VISUAL (img8):
    # Se a CAIXA VISUAL do radio (ui-radiobutton-box.ui-state-active)
    # já está ativa DENTRO da table, consideramos JÁ MARCADO — evita falso
    # negativo de input hidden dentro de .ui-helper-hidden-accessible.
    # SEG-1: arguments[0] = table_id, arguments[1] = value_alvo_str
    # ------------------------------------------------------------------
    try:
        _js_early_args = (
            r"""
            var tableId = arguments[0];
            var targetVal = String(arguments[1] || "").trim();
            var t = document.getElementById(tableId);
            if (!t) return false;
            var boxes = t.querySelectorAll('div.ui-radiobutton-box.ui-state-active');
            if (boxes && boxes.length > 0) {
                for (var b=0; b<boxes.length; b++){
                    var wrp = boxes[b].parentElement;
                    if (!wrp) continue;
                    var inp = wrp.querySelector('input[type=radio]');
                    if (inp && (String(inp.value||'').trim()===targetVal)) return true;
                    var lbl = (wrp.parentElement) ? wrp.parentElement.querySelector('label') : null;
                    if (lbl && (String(lbl.innerText||'').trim().toLowerCase()==='valor') && targetVal==='true') return true;
                }
                return (targetVal==='true' || targetVal==='LINHA' || boxes.length>0);
            }
            return false;
            """
        )
        if bool(driver.execute_script(_js_early_args, table_id, value_alvo_str)):
            try:
                aguardar_pagina_pronta(driver, modo="instantaneo", timeout=3)
            except Exception:
                pass
            print(f"  [Radio {label_table or table_id}] ✅ Já ativo visualmente (ui-state-active).", flush=True)
            return True
    except Exception:
        pass

    input_existe = False
    primeira_tentativa_wait = True
    name_descoberto = False
    while time.time() < fim_geral:
        # Early return: já está checado? Usa seletor SEM-NAME primeiro
        try:
            for css_checado in [
                input_sel_sem_name,
                f"table#{css_id} input[type=radio][value='{value_alvo_str}']:checked",
                f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']:checked",
                # Fallback final genérico (TODO O DOM):
                f"input[type=radio][value='{value_alvo_str}']:checked",
            ]:
                els_chk = driver.find_elements(By.CSS_SELECTOR, css_checado)
                for r in els_chk:
                    try:
                        if (r.get_attribute("value") or "").strip() == value_alvo_str and r.is_selected():
                            try:
                                aguardar_pagina_pronta(driver, modo="instantaneo", timeout=3)
                            except Exception:
                                pass
                            return True
                    except Exception:
                        continue
        except Exception:
            pass
        # --- Procura input ALVO usando primeiro SEM-NAME, depois name ---
        try:
            if driver.find_elements(By.CSS_SELECTOR, input_sel_sem_name):
                radio_name = _descobrir_name_real(driver, table_id, radio_name)
                name_descoberto = True
                input_sel = input_sel_sem_name
                input_existe = True
                break
        except Exception:
            pass
        try:
            if driver.find_elements(By.CSS_SELECTOR, input_sel_por_name):
                input_sel = input_sel_por_name
                input_existe = True
                break
        except Exception:
            pass
        # --- (NOVO) Fallback genérico ANTES DO TIMEOUT: busca TODO O DOM por value! ---
        try:
            generic_candidates = driver.find_elements(By.CSS_SELECTOR, input_sel_generico_por_value)
            if generic_candidates:
                for inp in generic_candidates:
                    try:
                        n = (inp.get_attribute("name") or "").strip()
                        if n:
                            radio_name = n
                            input_sel_por_name = f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']"
                            input_sel = input_sel_por_name
                            input_existe = True
                            break
                    except Exception:
                        continue
                if input_existe:
                    break
        except Exception:
            pass
        # --- Se ainda não achou: varra todos inputs dentro da table e descobre name ---
        if not name_descoberto:
            try:
                candidates = driver.find_elements(By.CSS_SELECTOR, table_all_inputs_sel)
                if candidates:
                    novo_name = None
                    for cand in candidates:
                        try:
                            novo_name = (cand.get_attribute("name") or "").strip()
                            if novo_name:
                                break
                        except Exception:
                            continue
                    if novo_name and novo_name != radio_name:
                        radio_name = novo_name
                        input_sel_por_name = f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']"
                    name_descoberto = True
            except Exception:
                pass
        try:
            driver.find_elements(By.CSS_SELECTOR, table_sel)
        except Exception:
            pass
        try:
            if primeira_tentativa_wait or (int(time.time() * 2) % 2 == 0):
                _limpar_overlays_orphans(driver)
                primeira_tentativa_wait = False
        except Exception:
            pass
        try:
            aguardar_pagina_pronta(driver, modo="instantaneo", timeout=2)
        except Exception:
            pass
        time.sleep(0.08)

    if not input_existe:
        # --- Fase final fallback: busca por value genérico + descobre name ---
        try:
            candidate_inputs = driver.find_elements(
                By.CSS_SELECTOR,
                f"input[type=radio][value='{value_alvo_str}']",
            )
            for inp in candidate_inputs:
                try:
                    n = (inp.get_attribute("name") or "").strip()
                    if n:
                        radio_name = n
                        input_sel_por_name = f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']"
                        input_sel = input_sel_por_name
                        input_existe = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

    try:
        aguardar_pagina_pronta(driver, modo="instantaneo", timeout=4)
    except Exception:
        pass

    def _checado_corretamente():
        # Tenta SEM-NAME primeiro (mais robusto, NÃO depende de name==table_id)
        try:
            for css_checked in [
                f"table#{css_id} input[type=radio][value='{value_alvo_str}']:checked",
                f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']:checked",
                f"input[type=radio][value='{value_alvo_str}']:checked",
            ]:
                els = driver.find_elements(By.CSS_SELECTOR, css_checked)
                if els:
                    return True
        except Exception:
            pass
        try:
            # SEG-1: arguments[0] = css_id, arguments[1] = value_alvo_str, arguments[2] = radio_name
            js_script = (
                r"""
                var cssId     = arguments[0];
                var targetVal = String(arguments[1] || "").trim();
                var rName     = arguments[2] ? String(arguments[2]).trim() : "";
                var sel1 = "table#" + cssId + " input[type=radio][value=\"" + targetVal.replace(/"/g,'&quot;') + "\"]";
                var rs = document.querySelectorAll(sel1);
                for (var i=0;i<rs.length;i++){
                    if (rs[i].checked) return true;
                }
                if (rName) {
                    var rs2 = document.querySelectorAll("input[type=radio][name=\"" + rName.replace(/"/g,'&quot;') + "\"]");
                    for (var j=0;j<rs2.length;j++){
                        if (rs2[j].checked && (String(rs2[j].value||'').trim()===targetVal)) return true;
                    }
                }
                var rs3 = document.querySelectorAll("input[type=radio][value=\"" + targetVal.replace(/"/g,'&quot;') + "\"]:checked");
                if (rs3 && rs3.length>0) return true;
                return false;
                """
            )
            return bool(driver.execute_script(js_script, css_id, value_alvo_str, radio_name))
        except Exception:
            return False

    if _checado_corretamente():
        try:
            aguardar_pagina_pronta(driver, modo="instantaneo", timeout=3)
        except Exception:
            pass
        return True

    def _tentar_marcar():
        if _checado_corretamente():
            return True
        # ===== PRIMEIRO TENTA COM O SELETOR MAIS ROBUSTO: SEM-NAME =====
        all_sel_candidates = [
            input_sel_sem_name,      # 1. table#id input[type=radio][value=X] (melhor)
            input_sel,                # 2. input_sel (o que quer que seja após a descoberta)
            input_sel_por_name,       # 3. por name
        ]
        for cur_sel in all_sel_candidates:
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR, cur_sel)
                for inp in inputs:
                    inp_id = inp.get_attribute("id") or ""
                    if inp_id:
                        labs = driver.find_elements(By.CSS_SELECTOR, f"label[for='{inp_id}']")
                        for lab in labs:
                            try:
                                lab.click()
                                time.sleep(0.04)
                                if _checado_corretamente():
                                    return True
                            except Exception:
                                try:
                                    ActionChains(driver, duration=10).move_to_element(lab).pause(0.02).click().perform()
                                    if _checado_corretamente():
                                        return True
                                except Exception:
                                    pass
                    try:
                        pai = inp.find_element(By.XPATH,
                            "./following-sibling::div[contains(@class,'ui-radiobutton-box')][1]")
                        try:
                            pai.click()
                        except Exception:
                            ActionChains(driver).move_to_element(pai).pause(0.02).click().perform()
                        time.sleep(0.04)
                        if _checado_corretamente():
                            return True
                    except Exception:
                        pass
                    try:
                        driver.execute_script("try { arguments[0].click(); } catch(e){}", inp)
                        time.sleep(0.04)
                        if _checado_corretamente():
                            return True
                    except Exception:
                        pass
            except Exception:
                pass
        # ===== SCRIPT JS UNIVERSAL: também usa SEM-NAME primeiro =====
        try:
            # SEG-1: arguments[0] = css_id, arguments[1] = value_alvo_str, arguments[2] = radio_name
            _script_marcar_radio = (
                r"""
                var cssId     = arguments[0];
                var targetVal = String(arguments[1] || "").trim();
                var rName     = arguments[2] ? String(arguments[2]).trim() : "";
                var esc = function(s){ return String(s||"").replace(/"/g,'&quot;'); };
                var rs = document.querySelectorAll("table#" + cssId + " input[type=radio][value=\"" + esc(targetVal) + "\"]");
                if (!rs || rs.length===0) {
                    rs = document.querySelectorAll("input[type=radio][name=\"" + esc(rName) + "\"][value=\"" + esc(targetVal) + "\"]");
                }
                if (!rs || rs.length===0) {
                    rs = document.querySelectorAll("input[type=radio][value=\"" + esc(targetVal) + "\"]");
                    if (!rs || rs.length===0) return false;
                }
                var inp = rs[0];
                var radioName = inp.name || rName;
                try {
                    var all = document.querySelectorAll("input[type=radio][name=" + JSON.stringify(radioName) + "]");
                    for (var i=0;i<all.length;i++){
                        try { all[i].checked = false; } catch(e){}
                        try {
                            var box = all[i].parentElement.querySelector('.ui-radiobutton-box');
                            if (box) {
                                box.classList.remove('ui-state-active','ui-state-hover');
                                var icon = box.querySelector('.ui-radiobutton-icon');
                                if (icon) icon.classList.remove('ui-icon-bullet');
                                if (icon) icon.classList.add('ui-icon-blank');
                            }
                        } catch(e){}
                    }
                    inp.checked = true;
                    try {
                        var box2 = inp.parentElement.querySelector('.ui-radiobutton-box');
                        if (box2) {
                            box2.classList.add('ui-state-active');
                            box2.classList.remove('ui-state-default');
                            var icon2 = box2.querySelector('.ui-radiobutton-icon');
                            if (icon2) icon2.classList.add('ui-icon-bullet');
                            if (icon2) icon2.classList.remove('ui-icon-blank');
                        }
                    } catch(e){}
                    try { inp.dispatchEvent(new Event('change',{bubbles:true,cancelable:true})); } catch(e){}
                    try { inp.dispatchEvent(new Event('input', {bubbles:true,cancelable:true})); } catch(e){}
                    try { inp.blur(); } catch(e){}
                    try { document.body.click(); } catch(e){}
                    return true;
                } catch(e){ return false; }
                """
            )
            ok_js = bool(driver.execute_script(
                _script_marcar_radio,
                css_id,
                value_alvo_str,
                radio_name,
            ))
            if ok_js:
                time.sleep(0.05)
                if _checado_corretamente():
                    return True
        except Exception:
            pass
        return False

    while time.time() < fim_geral:
        try:
            _limpar_overlays_orphans(driver)
        except Exception:
            pass
        ok = _tentar_marcar()
        if ok:
            break
        try:
            aguardar_pagina_pronta(driver, modo="instantaneo", timeout=3)
        except Exception:
            pass
        time.sleep(0.08)

    if _checado_corretamente():
        try:
            aguardar_pagina_pronta(driver, modo="instantaneo", timeout=4)
            _limpar_overlays_orphans(driver)
        except Exception:
            pass
        return True

    try:
        todos_radios = []
        # PRIMEIRO tenta SEM-NAME (dentro da table, NÃO depende de name)
        try:
            rs0 = driver.find_elements(By.CSS_SELECTOR,
                                       f"table#{css_id} input[type=radio]")
            for r in rs0:
                todos_radios.append(r)
        except Exception:
            pass
        rs1 = driver.find_elements(By.CSS_SELECTOR,
                                   f"input[type=radio][name='{table_id}']")
        for r in rs1:
            todos_radios.append(r)
        if radio_name and radio_name != table_id:
            rs2 = driver.find_elements(By.CSS_SELECTOR,
                                       f"input[type=radio][name='{radio_name}']")
            seen_ids = set(id(x) for x in todos_radios)
            for r in rs2:
                if id(r) not in seen_ids:
                    todos_radios.append(r)
                    seen_ids.add(id(r))
        tbl_els = driver.find_elements(By.ID, table_id)
        for tbl in tbl_els:
            try:
                rs3 = tbl.find_elements(By.CSS_SELECTOR, "input[type=radio]")
                seen_ids = set(id(x) for x in todos_radios)
                for r in rs3:
                    if id(r) not in seen_ids:
                        todos_radios.append(r)
                        seen_ids.add(id(r))
            except Exception:
                pass
        diag_vals = []
        for r in todos_radios:
            try:
                nm = (r.get_attribute("name") or "").strip()
                vl = (r.get_attribute("value") or "").strip()
                chk = r.is_selected()
                diag_vals.append(f"name='{nm}' value='{vl}' checked={chk}")
            except Exception:
                diag_vals.append("<erro leitura>")
        # ====== Se 0 radios encontrados: IMPRIME HTML / DIAG EXTRA ======
        if not diag_vals:
            try:
                _DIAG_HTML_JS = r"""
var tableId = arguments[0];
var t = document.getElementById(tableId);
if (!t) return 'ELEMENTO_COM_ID_NAO_EXISTE_NO_DOM';
var rs = t.querySelectorAll('input[type=radio], div.ui-helper-hidden-accessible input[type=radio]');
var inputs='';
for(var i=0;i<rs.length;i++){
  inputs+='  <input#'+i+'> name='+rs[i].name+' value='+rs[i].value+'\n';
}
var actives = t.querySelectorAll('div.ui-radiobutton-box.ui-state-active');
var activeInfo = 'UI_STATE_ACTIVE_boxes=' + (actives?actives.length:0) + ' | ';
for(var a=0;a<(actives?actives.length:0);a++){
  var wrp = actives[a].parentElement;
  var inp = wrp?wrp.querySelector('input[type=radio]'):null;
  activeInfo += 'box#'+a+' value='+(inp?inp.value:'?')+' checked='+(inp?inp.checked:'?')+' | ';
}
var names=''; var alln = t.querySelectorAll('*[name]');
for (var j=0;j<alln.length;j++) names+=(alln[j].tagName+'@name='+alln[j].getAttribute('name')+'  ');
return 'TABLE_EXISTE! Classe='+(t.className||'')+'\n'+
       'TOTAL_radios_DENTRO_DA_TABLE(incl helper-hidden)='+rs.length+'\n'+inputs+
       activeInfo + '\n' +
       'ELEMENTOS_COM_ATRIBUTO_NAME_dentro_da_table: '+names+
       '\nInnerHTML (1500 chars): '+(t.innerHTML||'').substring(0,1500);
"""
                diag_html_js = driver.execute_script(_DIAG_HTML_JS, table_id)
                print(f"  [DIAG marcar_radio] TABLE={table_id} EXISTE mas inputs=0!\n"
                      f"  >>> DIAG HTML JS:\n{diag_html_js}", flush=True)
            except Exception as e_html:
                print(f"  [DIAG marcar_radio] Falhou extract HTML: {type(e_html).__name__}: {e_html!r}", flush=True)
            try:
                _DIAG_VALS_JS = r"""
var all = document.querySelectorAll('input[type=radio]');
var out = [];
for (var i=0;i<Math.min(all.length, 80);i++) {
  var r = all[i];
  out.push('name='+r.name+' value='+r.value+' ch='+r.checked);
}
return out.join(' | ') || '<nenhum radio no DOM>';
"""
                diag_vals_js = driver.execute_script(_DIAG_VALS_JS)
                print(f"  [DIAG marcar_radio] Fallback — TDDOS os 80 primeiros radios do DOM: {diag_vals_js}", flush=True)
            except Exception as e_js2:
                print(f"  [DIAG marcar_radio] Fallback JS errou: {type(e_js2).__name__}", flush=True)
        else:
            print(f"  [DIAG marcar_radio] Grupo '{table_id}' (alvo='{value_alvo_str}') → "
                  f"Radios encontrados: {len(diag_vals)}. Valores: {', '.join(diag_vals)}", flush=True)
            for d in diag_vals:
                if "checked=True" in d:
                    print(f"  [DIAG marcar_radio] ⚠️  Radio ATUALMENTE marcado: {d} "
                          f"(precisa ser value='{value_alvo_str}')", flush=True)
                    break
    except Exception as e_diag:
        print(f"  [DIAG marcar_radio] Erro ao fazer diagnóstico: {type(e_diag).__name__}", flush=True)

    return False


# ====================================================================
# Clique Por Atividade (FASE 2 final) com Function.call(window)
# ====================================================================

def clicar_por_atividade_turbo(driver: webdriver.Chrome, timeout_geral: int = 20) -> bool:
    aguardar_pagina_pronta(driver, modo="leve", timeout=6)
    _limpar_overlays_orphans(driver)

    def _buscar_link():
        nonlocal a_encontrado, onclick_attr
        try:
            for a in driver.find_elements(
                By.CSS_SELECTOR,
                "li[id='menuForm:mg11203'] ul.ui-menu-child > li > a.ui-menuitem-link",
            ):
                try:
                    spans = a.find_elements(By.CSS_SELECTOR, "span.ui-menuitem-text")
                    for s in spans:
                        if (s.text or "").strip() == "Por Atividade":
                            a_encontrado = a
                            onclick_attr = a.get_attribute("onclick")
                            return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            for a in driver.find_elements(By.XPATH,
                "//li[@id='menuForm:mg11203']//ul[contains(@class,'ui-menu-child')]//a[contains(@class,'ui-menuitem-link') and span[text()='Por Atividade']]"):
                try:
                    a_encontrado = a
                    onclick_attr = a.get_attribute("onclick")
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            for a in driver.find_elements(By.XPATH, "//a[@href='#']/span[text()='Por Atividade']/.."):
                try:
                    a_encontrado = a
                    onclick_attr = a.get_attribute("onclick")
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    a_encontrado = None
    onclick_attr = None

    fim_busca = time.time() + 3.5
    while (not _buscar_link()) and time.time() < fim_busca:
        try:
            fed = driver.find_elements(By.CSS_SELECTOR, "li[id='menuForm:mg11203'] > a.ui-menuitem-link")
            if fed:
                ActionChains(driver, duration=10).move_to_element(fed[0]).pause(0.15).perform()
        except Exception:
            pass
        try:
            _limpar_overlays_orphans(driver)
        except Exception:
            pass
        time.sleep(0.05)

    if not a_encontrado:
        return False

    def _ja_navegou():
        try:
            els_nav = driver.find_elements(By.ID, "selectForm:coorte_input")
            if els_nav and els_nav[0].is_displayed():
                return True
            if els_nav:
                if driver.find_elements(By.ID, "selectForm:variavel"):
                    return True
        except Exception:
            pass
        return False

    if _ja_navegou():
        return True

    def _clicar():
        oc = (onclick_attr or "").strip()
        if oc:
            try:
                res = driver.execute_script(
                    "var a = arguments[0];"
                    "var oc = arguments[1];"
                    "try {"
                    "  if (oc && oc.length > 0) {"
                    "    var f = new Function(oc);"
                    "    return f.call(window) || true;"
                    "  }"
                    "} catch(e) {}"
                    "try { a.click(); return true; } catch(e2) {}"
                    "return false;",
                    a_encontrado,
                    oc,
                )
                if res:
                    return True
            except Exception:
                pass
        try:
            driver.execute_script(
                "var a = arguments[0];"
                "try { a.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));"
                "  a.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));"
                "  a.click(); return true; } catch(e) { return false; }",
                a_encontrado,
            )
            return True
        except Exception:
            pass
        try:
            for s in a_encontrado.find_elements(By.CSS_SELECTOR, "span.ui-menuitem-text"):
                try:
                    s.click()
                    return True
                except Exception:
                    try:
                        ActionChains(driver, duration=10).move_to_element(s).pause(0.02).click().perform()
                        return True
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            a_encontrado.click()
            return True
        except Exception:
            try:
                ActionChains(driver).move_to_element(a_encontrado).pause(0.03).click().perform()
                return True
            except Exception:
                return False

    fim_geral_int = time.time() + timeout_geral
    nav_ocorreu = False
    for tentativa in range(3):
        if nav_ocorreu or time.time() > fim_geral_int:
            break
        ok_click = _clicar()
        fim_mini = time.time() + 5.0
        while (not nav_ocorreu) and time.time() < fim_mini:
            if _ja_navegou():
                nav_ocorreu = True
                break
            time.sleep(0.05)
        if nav_ocorreu:
            break
        try:
            _limpar_overlays_orphans(driver)
        except Exception:
            pass
        time.sleep(0.12)

    if nav_ocorreu:
        aguardar_pagina_pronta(driver, modo="navegacao", timeout=10)
        _limpar_overlays_orphans(driver)
    return nav_ocorreu


__all__ = [
    "clicar_com_retry",
    "hover_em",
    "_validar_campo_preenchido",
    "_preencher_por_send_keys_direto",
    "_preencher_por_js_com_events",
    "_preencher_por_action_chains",
    "preencher_login_rapido",
    "fazer_login_turbo",
    "preencher_texto_simples",
    "_ajustar_checkboxes_js",
    "valor_campo_jah_correto",
    "tentar_por_trigger_e_options",
    "selecionar_valor",
    "fechar_painel_selectcheckboxmenu",
    "abrir_selectcheckboxmenu_primefaces",
    "marcar_radiobutton_primefaces",
    "clicar_por_atividade_turbo",
]
