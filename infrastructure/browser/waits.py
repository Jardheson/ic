"""
Helpers de SINCRONIZAÇÃO e ESPERA da automação CNI.

100% DO CÓDIGO JS e LÓGICA extraído INTACTO de main_monolith_backup.py.
ÚNICA ALTERAÇÃO: `driver` é o PRIMEIRO parâmetro de TODAS as funções
(em vez de variável global do monólito).

Inclui:
- Engine multi-perfil aguardar_pagina_pronta (instantaneo/leve/rapido/navegacao/normal/estrito)
- _SCRIPT_CHECK_PAGE (1 JS roundtrip → AJAX + overlays + body sig)
- _SCRIPT_CLEAR_OVERLAYS + escape de overlays órfãos JSF
- aguardar_ajax / esperar_estavel / aguardar_navegacao
- Detectores de tela: _na_tela_login / _pegou_erro_login / aguardar_tela_inicial
- fechar_popups_e_dialogos / _checar_mensagem_obrigatorio
"""
from __future__ import annotations

import time
import re
from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementNotInteractableException,
)

from config.constants import PERFIS

# ====================================================================
# SCRIPTS JS MULTILINHA INTACTOS (NÃO ALTERAR!)
# ====================================================================

_SCRIPT_CHECK_PAGE = """
(function () {
  // 1) AJAX: jQuery.active + PrimeFaces.ajax.Queue + document.readyState + __ajaxCount
  var ajax0 = true;
  try { if (typeof jQuery !== 'undefined' && jQuery.active !== 0) ajax0 = false; } catch(e){}
  try {
    if (typeof PrimeFaces !== 'undefined' && PrimeFaces.ajax && !PrimeFaces.ajax.Queue.isEmpty())
      ajax0 = false;
  } catch(e){}
  try { if (document.readyState !== 'complete') ajax0 = false; } catch(e){}
  try { if (typeof window.__ajaxCount !== 'undefined' && window.__ajaxCount !== 0) ajax0 = false; } catch(e){}

  // 2) Overlays / spinners (checa em 1 batida — usa selector único)
  var sel =
    'div.ui-blockui,' +
    'div.ui-dialog-content ~ div.ui-widget-overlay,' +
    '.ui-autocomplete-loading,' +
    '.ui-datatable-loading,' +
    '.ui-fileupload-loading,' +
    '[class*="loading"]:not([class*="loaded"]),' +
    '[class*="spinner"]:not([class*="spinner-loaded"]),' +
    '.ui-progressbar[aria-valuenow]:not([aria-valuenow="100"])';
  var overlaysLimpos = true;
  try {
    var list = document.querySelectorAll(sel);
    for (var i = 0; i < list.length; i++) {
      var n = list[i];
      if (!n || !n.getClientRects || !n.getClientRects().length) continue;
      var r = n.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        var st = window.getComputedStyle(n);
        if (!st || st.visibility === 'hidden' || st.display === 'none' || parseFloat(st.opacity || '1') < 0.05) continue;
        overlaysLimpos = false;
        break;
      }
    }
  } catch(e) { overlaysLimpos = true; }

  // 3) Assinatura curta do body para detectar DOM estacionário (soma de comprimentos)
  var sig = 0;
  try {
    var bd = document.body;
    if (bd) {
      sig = (bd.childElementCount * 131) ^
            (bd.innerHTML.length & 0x7fffffff) ^
            (bd.innerHTML.slice(0, 160).length);
    }
  } catch(e) {}

  return [ajax0, overlaysLimpos, sig];
})();
"""

_SCRIPT_CLEAR_OVERLAYS = """
(function () {
  var killed = 0;
  try {
    var nodes = document.querySelectorAll('div.ui-blockui, div.ui-widget-overlay, div.ui-dialog-overlay');
    for (var i = 0; i < nodes.length; i++) {
      try {
        nodes[i].style.display = 'none';
        nodes[i].style.visibility = 'hidden';
        nodes[i].style.zIndex = '-1';
        nodes[i].removeAttribute('class');
        killed++;
      } catch (e) {}
    }
  } catch (e) {}
  try { if (window.PrimeFaces && PrimeFaces.widgets) { Object.keys(PrimeFaces.widgets).forEach(function(k){ var w = PrimeFaces.widgets[k]; if (w && typeof w.hide === 'function' && (w.cfg && (w.cfg.blockUI || /block/i.test(k)))) { try { w.hide(); killed++; } catch(e){} } }); } } catch(e){}
  return killed;
})();
"""


# ====================================================================
# Helpers de status de página
# ====================================================================

def _pagina_status(driver: webdriver.Chrome) -> Tuple[bool, bool, int]:
    """Retorna (ajax_ok, overlays_ok, body_sig) em 1 ÚNICA chamada JS (roundtrip único)."""
    try:
        r = driver.execute_script(_SCRIPT_CHECK_PAGE)
        return bool(r[0]), bool(r[1]), int(r[2])
    except Exception:
        return False, False, 0


def _sem_overlays_de_carregamento(driver: webdriver.Chrome) -> bool:
    return _pagina_status(driver)[1]


def _ajax_em_repouso(driver: webdriver.Chrome) -> bool:
    return _pagina_status(driver)[0]


def _elemento_habilitado(el) -> bool:
    try:
        if el.get_attribute("disabled") is not None:
            return False
        if el.get_attribute("aria-disabled") == "true":
            return False
        if el.get_attribute("readonly") is not None and el.tag_name.lower() in ("input", "select", "textarea"):
            return False
        cls = (el.get_attribute("class") or "").lower()
        if "ui-state-disabled" in cls or "disabled" in cls.split():
            return False
        return True
    except (StaleElementReferenceException, Exception):
        return False


def _limpar_overlays_orphans(driver: webdriver.Chrome) -> int:
    try:
        return int(driver.execute_script(_SCRIPT_CLEAR_OVERLAYS) or 0)
    except Exception:
        return 0


def _locator_to_css(locator) -> Optional[str]:
    by, value = locator
    if by == By.CSS_SELECTOR:
        return value
    if by == By.ID:
        escaped = re.sub(r"([^\w-])", r"\\\1", value)
        return f"#{escaped}"
    if by == By.XPATH:
        m = re.match(r"^//\*\[@id=['\"]([^'\"]+)['\"]\]$", value)
        if m:
            escaped = re.sub(r"([^\w-])", r"\\\1", m.group(1))
            return f"#{escaped}"
        m = re.match(r"^//([a-zA-Z][\w-]*)\[@type=['\"]([^'\"]+)['\"]\]$", value)
        if m:
            return f"{m.group(1)}[type='{m.group(2)}']"
    return None


# ====================================================================
# Detectores de tela (login/erro)
# ====================================================================

def _na_tela_login(driver: webdriver.Chrome) -> bool:
    try:
        url = driver.current_url or ""
        if "/login" in url.lower():
            return True
        if driver.execute_script(
            "return !!(document.getElementById('loginForm:formLogin_btnLogin') || "
            "document.querySelector(\"input[type='password']\"));"):
            return True
    except Exception:
        pass
    return False


def _pegou_erro_login(driver: webdriver.Chrome) -> Tuple[bool, str]:
    try:
        txt = driver.execute_script(
            "var m='', sels=['[class*=error]','[class*=message-error]','[role=alert]',"
            "'.ui-messages-error-detail','.ui-message-error',"
            "'[class*=\"Erro\"]','[class*=invalido]','[class*=credenciais'];"
            "sels.forEach(function(s){ document.querySelectorAll(s).forEach(function(n){ "
            "if (n.offsetParent !== null || n.getClientRects().length){ m += ' ' + (n.innerText||n.textContent||''); } }); });"
            "return m.toLowerCase().slice(0,400);"
        )
    except Exception:
        txt = ""
    if not txt:
        return False, ""
    for palavra in ["erro", "inválido", "invalido", "incorreta", "incorreto", "credenciais",
                    "senha", "usuário", "usuario", "obrigatório", "obrigatorio",
                    "bloqueado", "sessão expirou", "sessao expirou"]:
        if palavra in txt:
            return True, txt.strip()
    return False, txt.strip()


# ====================================================================
# Engine principal: aguardar_pagina_pronta (multi-perfil)
# ====================================================================

def aguardar_pagina_pronta(
    driver: webdriver.Chrome,
    modo: str = "normal",
    timeout: Optional[int] = None,
    janela_estavel: Optional[float] = None,
) -> None:
    perfil = PERFIS.get(modo, PERFIS["normal"])
    timeout_val = timeout if timeout is not None else perfil["timeout"]
    fim = time.time() + timeout_val
    janela = janela_estavel if janela_estavel is not None else perfil["janela"]
    usar_hash = perfil.get("usar_hash", True)
    hash_janela = perfil["hash_janela"] if usar_hash else 0.0
    poll = perfil["poll"]
    overlay_escape = perfil.get("overlay_escape", 15.0)
    pronto_desde = None
    ultimo_sig = None
    sig_estavel_desde = None
    overlays_bloqueando_desde = None
    ultima_limpeza = 0.0

    if modo == "instantaneo":
        _pagina_status(driver)
        return

    while True:
        agora = time.time()
        if agora > fim:
            return
        ajax_ok, overlays_ok, body_sig = _pagina_status(driver)

        # LIMPEZA ATIVA: overlays órfãos de JSF/PrimeFaces
        if not overlays_ok:
            if overlays_bloqueando_desde is None:
                overlays_bloqueando_desde = agora
            permaneceu = agora - overlays_bloqueando_desde
            if permaneceu >= 4.0 and (agora - ultima_limpeza) >= 1.0:
                try:
                    _limpar_overlays_orphans(driver)
                except Exception:
                    pass
                ultima_limpeza = agora
            if permaneceu >= overlay_escape:
                overlays_ok = True
        else:
            overlays_bloqueando_desde = None

        hash_ok = True
        if usar_hash:
            if body_sig and body_sig == ultimo_sig:
                if sig_estavel_desde is None:
                    sig_estavel_desde = agora
            else:
                sig_estavel_desde = None
                ultimo_sig = body_sig
            hash_ok = (sig_estavel_desde is not None) and ((agora - sig_estavel_desde) >= hash_janela)

        if ajax_ok and overlays_ok and hash_ok:
            if janela <= 0:
                return
            if pronto_desde is None:
                pronto_desde = agora
            elif agora - pronto_desde >= janela:
                return
        else:
            pronto_desde = None
        time.sleep(poll)


# ====================================================================
# Popups / dialogs
# ====================================================================

def fechar_popups_e_dialogos(driver: webdriver.Chrome) -> int:
    fechados = 0
    alvos = [
        ".ui-dialog-titlebar-close",
        ".ui-dialog .ui-icon-closethick",
        "button.ui-notification-close",
        ".ui-growl-item-container .ui-icon-closethick",
        ".ui-messages-close",
        ".ui-overlay-close",
        "[aria-label='Fechar']",
        "[data-icon='close']",
    ]
    for sel in alvos:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                try:
                    if el.is_displayed():
                        try:
                            el.click()
                            fechados += 1
                            time.sleep(0.05)
                        except (StaleElementReferenceException, ElementNotInteractableException):
                            try:
                                driver.execute_script("arguments[0].click();", el)
                                fechados += 1
                                time.sleep(0.05)
                            except Exception:
                                pass
                except (StaleElementReferenceException, Exception):
                    continue
        except Exception:
            continue
    # Remove qualquer blockUI órfão que ficou visível com display:block mas sem ação
    try:
        driver.execute_script(
            "document.querySelectorAll('div.ui-blockui, div.ui-widget-overlay').forEach(function(n){ "
            "  try { n.style.display='none'; n.removeAttribute('class'); } catch(e){} });"
        )
    except Exception:
        pass
    if fechados > 0:
        print(f"Limpeza pós-login: {fechados} popup(s)/dialog(s) fechado(s).", flush=True)
    return fechados


# ====================================================================
# Wrappers passo menu (para FASE 2 navegação)
# ====================================================================

def passo_hover_menu(
    driver: webdriver.Chrome,
    titulo: str,
    fn_hover,
    locator_proximo=None,
) -> None:
    print(f"{titulo} ...", flush=True)
    aguardar_pagina_pronta(driver, modo="leve")
    t0 = time.time()
    try:
        fn_hover()
    except Exception as e:
        dt = time.time() - t0
        print(f"{titulo} ({dt:.2f}s) → {type(e).__name__}: {e}", flush=True)
        raise
    if locator_proximo is not None:
        try:
            WebDriverWait(driver, 3).until(EC.visibility_of_element_located(locator_proximo))
        except Exception:
            pass
    else:
        time.sleep(0.08)
    dt = time.time() - t0
    print(f"{titulo} ({dt:.2f}s)", flush=True)


def passo_clique_menu(
    driver: webdriver.Chrome,
    titulo: str,
    fn,
    depois_nav: bool = False,
):
    print(f"{titulo} ...", flush=True)
    aguardar_pagina_pronta(driver, modo="leve")
    t0 = time.time()
    try:
        resultado = fn()
    except Exception as e:
        dt = time.time() - t0
        print(f"{titulo} ({dt:.2f}s) → {type(e).__name__}: {e}", flush=True)
        raise
    if depois_nav:
        aguardar_pagina_pronta(driver, modo="navegacao")
    else:
        aguardar_pagina_pronta(driver, modo="leve")
    dt = time.time() - t0
    print(f"{titulo} ({dt:.2f}s)", flush=True)
    return resultado


def passo(
    driver: webdriver.Chrome,
    titulo: str,
    fn,
    *args,
    modo_antes: Optional[str] = "leve",
    modo_depois: Optional[str] = "leve",
    **kwargs,
):
    print(f"{titulo} ...", flush=True)
    if modo_antes is not None:
        aguardar_pagina_pronta(driver, modo=modo_antes)
    t0 = time.time()
    try:
        resultado = fn(*args, **kwargs)
    except Exception as e:
        dt = time.time() - t0
        print(f"{titulo} ({dt:.2f}s) → {type(e).__name__}: {e}", flush=True)
        raise
    if modo_depois is not None:
        aguardar_pagina_pronta(driver, modo=modo_depois)
    dt = time.time() - t0
    print(f"{titulo} ({dt:.2f}s)", flush=True)
    return resultado


# ====================================================================
# Waits específicos: AJAX, estável, navegação, tela inicial
# ====================================================================

def aguardar_tela_inicial(
    driver: webdriver.Chrome,
    url_esperada: Optional[str] = None,
    timeout: int = 14,
) -> None:
    loc_pwd = (By.CSS_SELECTOR, "input[type='password']")
    loc_btn = (By.ID, "loginForm:formLogin_btnLogin")
    fim = time.time() + timeout
    ult_over = 0.0
    pronto_interativo = False

    while time.time() < fim:
        if time.time() - ult_over > 2.0:
            try:
                _limpar_overlays_orphans(driver)
            except Exception:
                pass
            ult_over = time.time()
        if not pronto_interativo:
            try:
                rs = driver.execute_script(
                    "var s = document.readyState; return (s==='interactive' || s==='complete') ? s : null;"
                )
                if rs:
                    pronto_interativo = True
            except Exception:
                pass
        if pronto_interativo:
            try:
                if (len(driver.find_elements(*loc_pwd)) > 0
                        or len(driver.find_elements(*loc_btn)) > 0):
                    break
            except Exception:
                pass
        time.sleep(0.05)

    t_rest = max(1.0, min(6.0, fim - time.time()))
    try:
        WebDriverWait(driver, t_rest, poll_frequency=0.05).until(
            EC.presence_of_element_located(loc_pwd)
        )
    except Exception:
        pass

    try:
        _limpar_overlays_orphans(driver)
        _limpar_overlays_orphans(driver)
    except Exception:
        pass
    try:
        fechar_popups_e_dialogos(driver)
    except Exception:
        pass


def aguardar_ajax(driver: webdriver.Chrome, grace: float = 0.02) -> None:
    fim = time.time() + 6
    while time.time() < fim:
        if _ajax_em_repouso(driver):
            time.sleep(grace)
            return
        time.sleep(0.025)
    time.sleep(grace)


def esperar_estavel(driver: webdriver.Chrome, locator, timeout: int = 4):
    limite = time.time() + timeout
    ultima_pos = None
    ultima_dimensao = None
    estavel_desde = None
    ultra_short_wait = WebDriverWait(driver, 3, poll_frequency=0.02)
    while True:
        try:
            el = driver.find_element(*locator)
            if not el.is_displayed():
                estavel_desde = None
                time.sleep(0.015)
                continue
            if not _elemento_habilitado(el):
                estavel_desde = None
                time.sleep(0.015)
                continue
            rect = el.rect
            pos = (rect["x"], rect["y"])
            dim = (rect["width"], rect["height"])
            if pos == ultima_pos and dim == ultima_dimensao and rect["width"] > 0 and rect["height"] > 0:
                if estavel_desde is None:
                    estavel_desde = time.time()
                elif time.time() - estavel_desde >= 0.08:
                    return el
            else:
                estavel_desde = None
                ultima_pos = pos
                ultima_dimensao = dim
        except (StaleElementReferenceException, Exception):
            estavel_desde = None
            ultima_pos = None
            ultima_dimensao = None
        if time.time() > limite:
            try:
                return driver.find_element(*locator)
            except Exception:
                return None
        time.sleep(0.02)


def aguardar_navegacao(
    driver: webdriver.Chrome,
    anterior=None,
    timeout: int = 12,
) -> None:
    fim = time.time() + timeout
    if anterior is not None:
        while time.time() < fim:
            try:
                if anterior.is_displayed():
                    time.sleep(0.05)
                    continue
            except StaleElementReferenceException:
                break
            except Exception:
                pass
            time.sleep(0.03)
    aguardar_pagina_pronta(
        driver,
        modo="normal",
        timeout=max(4, int(fim - time.time())),
    )


# ====================================================================
# Detector de mensagens obrigatório
# ====================================================================

def _checar_mensagem_obrigatorio(driver: webdriver.Chrome) -> bool:
    mensagens = [
        "[class*='error']",
        "[class*='message-error']",
        "[class*='faces-message']",
        ".ui-message-error",
        ".ui-messages-error-detail",
        "[role='alert']",
    ]
    for sel in mensagens:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                try:
                    txt = (el.text or "").lower()
                    if not el.is_displayed():
                        continue
                    if "obrigatório" in txt or "obrigatorio" in txt or "preenchimento" in txt:
                        return True
                except (StaleElementReferenceException, Exception):
                    continue
        except Exception:
            continue
    return False


__all__ = [
    "_SCRIPT_CHECK_PAGE",
    "_SCRIPT_CLEAR_OVERLAYS",
    "_pagina_status",
    "_sem_overlays_de_carregamento",
    "_ajax_em_repouso",
    "_elemento_habilitado",
    "_limpar_overlays_orphans",
    "_locator_to_css",
    "_na_tela_login",
    "_pegou_erro_login",
    "aguardar_pagina_pronta",
    "fechar_popups_e_dialogos",
    "passo_hover_menu",
    "passo_clique_menu",
    "passo",
    "aguardar_tela_inicial",
    "aguardar_ajax",
    "esperar_estavel",
    "aguardar_navegacao",
    "_checar_mensagem_obrigatorio",
]
