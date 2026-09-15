import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException

# Inicialização do Navegador e ferramentas de suporte
driver = webdriver.Chrome()
driver.maximize_window()
actions = ActionChains(driver)

# URL de acesso direto ao sistema de Sondagens da CNI
driver.get("https://pesquisasconjunturais.cni.com.br/Sondagens/view/index.faces")
wait = WebDriverWait(driver, 12)
short_wait = WebDriverWait(driver, 5)
ultra_short_wait = WebDriverWait(driver, 3, poll_frequency=0.02)

# Credenciais institucionais configuradas
SEU_USUARIO = ""
SUA_SENHA = ""

# -------------------------------------------------------------
# ÁRVORE DE WAITS: Utilitários de sincronização robusta (Originais)
# -------------------------------------------------------------

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

def _pagina_status():
    """Retorna (ajax_ok, overlays_ok, body_sig) em 1 ÚNICA chamada JS (roundtrip único)."""
    try:
        r = driver.execute_script(_SCRIPT_CHECK_PAGE)
        return bool(r[0]), bool(r[1]), int(r[2])
    except Exception:
        return False, False, 0

def _sem_overlays_de_carregamento():
    return _pagina_status()[1]

def _ajax_em_repouso():
    return _pagina_status()[0]

def _elemento_habilitado(el):
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

_PERFIS = {
    "instantaneo": {"janela": 0.00, "hash_janela": 0.00, "poll": 0.015, "timeout": 3,  "usar_hash": False, "overlay_escape": 4.0},
    "leve":       {"janela": 0.005,"hash_janela": 0.00, "poll": 0.015, "timeout": 5,  "usar_hash": False, "overlay_escape": 5.0},
    "rapido":     {"janela": 0.02, "hash_janela": 0.00, "poll": 0.02,  "timeout": 7,  "usar_hash": False, "overlay_escape": 6.0},
    "navegacao":  {"janela": 0.05, "hash_janela": 0.02, "poll": 0.025, "timeout": 12, "usar_hash": True,  "overlay_escape": 8.0},
    "normal":     {"janela": 0.08, "hash_janela": 0.04, "poll": 0.03,  "timeout": 18, "usar_hash": True,  "overlay_escape": 10.0},
    "estrito":    {"janela": 0.15, "hash_janela": 0.08, "poll": 0.04,  "timeout": 30, "usar_hash": True,  "overlay_escape": 14.0},
}

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

def _limpar_overlays_orphans():
    try:
        return int(driver.execute_script(_SCRIPT_CLEAR_OVERLAYS) or 0)
    except Exception:
        return 0

def _na_tela_login():
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

def _pegou_erro_login():
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

def aguardar_pagina_pronta(modo="normal", timeout=None, janela_estavel=None):
    perfil = _PERFIS.get(modo, _PERFIS["normal"])
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
        _pagina_status()
        return

    while True:
        agora = time.time()
        if agora > fim:
            return
        ajax_ok, overlays_ok, body_sig = _pagina_status()

        # LIMPEZA ATIVA: overlays órfãos de JSF/PrimeFaces
        if not overlays_ok:
            if overlays_bloqueando_desde is None:
                overlays_bloqueando_desde = agora
            permaneceu = agora - overlays_bloqueando_desde
            if permaneceu >= 4.0 and (agora - ultima_limpeza) >= 1.0:
                try:
                    _limpar_overlays_orphans()
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

def fechar_popups_e_dialogos():
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

def clicar_por_atividade_turbo(timeout_geral=20):
    """Clica no item 'Por Atividade' (SUBMIT do menuForm) com CONFIABILIDADE MÁXIMA.
       - Acha o link EXATO filho de li#menuForm:mg11203 (Federação) → ul.ui-menu-child → li → a.ui-menuitem-link
         com span.ui-menuitem-text == 'Por Atividade'.
       - 3 estratégias de clique em ordem:
         1) JS native: executar o próprio onclick do <a> usando Function(attr.onclick).call(a)
         2) JS native: a.click()
         3) Fallback Selenium clicar no label span ou no <a>.
       - Após o clique, espera STALENESS de menuForm OU mudança de URL OU presença do campo
         Coorte no form selectForm (todos indicam que o POST submit foi processado).
    """
    # ------------------------------------------------------------------
    # 0. Limpeza overlays + página pronta antes
    # ------------------------------------------------------------------
    aguardar_pagina_pronta(modo="leve", timeout=6)
    _limpar_overlays_orphans()

    # Locator EXATO do link Por Atividade:
    #   li#menuForm:mg11203 (Federação) → ul.ui-menu-child → li → a.ui-menuitem-link com span "Por Atividade"
    # Também aceita a procuramos via spans com texto exato
    css_link_filho = (
        "li[id='menuForm:mg11203'] ul.ui-menu-child > li > a.ui-menuitem-link,"
        "li[id='menuForm:mg11203'] > ul > li > a[href='#'],"
        "li.ui-menuitem a.ui-menuitem-link > span.ui-menuitem-text"
    )
    css_por_atividade_especifico = (
        "li[id='menuForm:mg11203'] ul.ui-menu-child > li > a.ui-menuitem-link:has(span[textContent='Por Atividade']),"
        "li[id='menuForm:mg11203'] > ul > li > a[href='#'] > span.ui-menuitem-text"
    )
    a_encontrado = None  # WebElement
    onclick_attr = None  # str

    # ------------------------------------------------------------------
    # 1. Encontrar o elemento <a> correto
    # ------------------------------------------------------------------
    def _buscar_link():
        nonlocal a_encontrado, onclick_attr
        # Estratégia 1: CSS selector exato
        try:
            for a in driver.find_elements(By.CSS_SELECTOR,
                                          "li[id='menuForm:mg11203'] ul.ui-menu-child > li > a.ui-menuitem-link"):
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
        # Estratégia 2: XPath exato
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
        # Estratégia 3: por todos os <a> com texto Por Atividade
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

    # Buscar por até 3.5s (se o submenu demorar a abrir)
    fim_busca = time.time() + 3.5
    while (not _buscar_link()) and time.time() < fim_busca:
        # Refaz o hover no Federação para garantir que o submenu não fechou
        try:
            ac = ActionChains(driver, duration=10)
            fed = driver.find_elements(By.CSS_SELECTOR, "li[id='menuForm:mg11203'] > a.ui-menuitem-link")
            if fed:
                ac.move_to_element(fed[0]).pause(0.15).perform()
        except Exception:
            pass
        try:
            _limpar_overlays_orphans()
        except Exception:
            pass
        time.sleep(0.05)

    if not a_encontrado:
        return False

    # ------------------------------------------------------------------
    # 2. Detectar se já clicou (nav aconteceu)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 3. 3 estratégias de clique
    # ------------------------------------------------------------------
    def _clicar():
        # 3.1) Executar o onclick literal via Function.call no escopo global window
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
                    a_encontrado, oc
                )
                if res:
                    return True
            except Exception:
                pass
        # 3.2) click JS
        try:
            driver.execute_script(
                "var a = arguments[0];"
                "try { a.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,view:window}));"
                "  a.dispatchEvent(new MouseEvent('mouseup',{bubbles:true,cancelable:true,view:window}));"
                "  a.click(); return true; } catch(e) { return false; }",
                a_encontrado
            )
            return True
        except Exception:
            pass
        # 3.3) Selenium puro (no span filho, mais provável de não ser interceptado)
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

    fim_geral = time.time() + timeout_geral
    nav_ocorreu = False
    for tentativa in range(3):
        if nav_ocorreu or time.time() > fim_geral:
            break
        ok_click = _clicar()
        # Espera até 5s por navegação pós click
        fim_mini = time.time() + 5.0
        while (not nav_ocorreu) and time.time() < fim_mini:
            if _ja_navegou():
                nav_ocorreu = True
                break
            time.sleep(0.05)
        if nav_ocorreu:
            break
        # Quebra blockUI órfão antes de próxima tentativa
        try:
            _limpar_overlays_orphans()
        except Exception:
            pass
        time.sleep(0.12)

    if nav_ocorreu:
        aguardar_pagina_pronta(modo="navegacao", timeout=10)
        _limpar_overlays_orphans()
    return nav_ocorreu

def passo_hover_menu(titulo, fn_hover, locator_proximo=None):
    """Wrapper leve para HOVER em menus:
       - ANTES: só espera AJAX 0 + sem overlays (modo 'leve')
       - Ação: hover() via ActionChain
       - DEPOIS: wait curto (0.08s) + se houver locator_proximo, espera ele ficar visível
       NÃO roda aguardar_pagina_pronta completo (hash + janela)
    """
    print(f"{titulo} ...", flush=True)
    aguardar_pagina_pronta(modo="leve")
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

def passo_clique_menu(titulo, fn, depois_nav=False):
    """Wrapper leve para CLIQUE em item de menu:
       - ANTES: 'leve'
       - DEPOIS: se depois_nav=True usa 'navegacao', senão 'leve'
    """
    print(f"{titulo} ...", flush=True)
    aguardar_pagina_pronta(modo="leve")
    t0 = time.time()
    try:
        resultado = fn()
    except Exception as e:
        dt = time.time() - t0
        print(f"{titulo} ({dt:.2f}s) → {type(e).__name__}: {e}", flush=True)
        raise
    if depois_nav:
        aguardar_pagina_pronta(modo="navegacao")
    else:
        aguardar_pagina_pronta(modo="leve")
    dt = time.time() - t0
    print(f"{titulo} ({dt:.2f}s)", flush=True)
    return resultado

def aguardar_tela_inicial(url_esperada=None, timeout=14):
    """TELA INICIAL ULTRA-RÁPIDA.
       NÃO espera performance.timing.loadEventEnd (gargalo em JSF/SPA,
       pode ficar 0 por 60s se houver iframe/tracking/recursos lentos).
       Espera SÓ o que importa para o login:
         1) DOM carregado (readyState == 'interactive' ou 'complete')
         2) input[type=password] EXISTE no DOM (1 WebDriverWait)
       Limpeza de overlays: a cada 2s no loop, e UMA vez no final.
       Timeout total padrão: 14s.
    """
    loc_pwd = (By.CSS_SELECTOR, "input[type='password']")
    loc_btn = (By.ID, "loginForm:formLogin_btnLogin")
    fim = time.time() + timeout
    ult_over = 0.0
    pronto_interativo = False

    while time.time() < fim:
        # Limpeza overlays órfãos a cada 2s
        if time.time() - ult_over > 2.0:
            try:
                _limpar_overlays_orphans()
            except Exception:
                pass
            ult_over = time.time()
        # readyState só precisa ser interactive ou complete (não 'loading')
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
            # O que realmente importa: existe o password OU o botão?
            try:
                if (len(driver.find_elements(*loc_pwd)) > 0
                        or len(driver.find_elements(*loc_btn)) > 0):
                    break
            except Exception:
                pass
        time.sleep(0.05)

    # Última garantia: espera PRESENÇA do password por até (timeout restante, máx 6s)
    t_rest = max(1.0, min(6.0, fim - time.time()))
    try:
        WebDriverWait(driver, t_rest, poll_frequency=0.05).until(
            EC.presence_of_element_located(loc_pwd)
        )
    except Exception:
        pass

    # LIMPEZA FINAL forte de overlays + skip aguardar_pagina_pronta (não precisa mais)
    try:
        _limpar_overlays_orphans()
        _limpar_overlays_orphans()
    except Exception:
        pass
    try:
        fechar_popups_e_dialogos()
    except Exception:
        pass

def aguardar_ajax(grace=0.02):
    fim = time.time() + 6
    while time.time() < fim:
        if _ajax_em_repouso():
            time.sleep(grace)
            return
        time.sleep(0.025)
    time.sleep(grace)

def esperar_estavel(locator, timeout=4):
    limite = time.time() + timeout
    ultima_pos = None
    ultima_dimensao = None
    estavel_desde = None
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

def clicar_com_retry(locator, tentativas=3):
    ultimo_erro = None
    for i in range(tentativas):
        try:
            esperar_estavel(locator, timeout=3)
            el = ultra_short_wait.until(EC.element_to_be_clickable(locator))
            if not _elemento_habilitado(el):
                time.sleep(0.05)
                continue
            try:
                driver.execute_script("try { arguments[0].click(); return true; } catch(e){ return false; }", el)
            except Exception:
                el.click()
            return
        except (StaleElementReferenceException, ElementNotInteractableException) as e:
            ultimo_erro = e
            time.sleep(0.05)
    raise ultimo_erro if ultimo_erro else RuntimeError(f"Falha clicar_com_retry em {locator}")

def hover_em(locator, tentativas=3):
    ultimo_erro = None
    for i in range(tentativas):
        try:
            esperar_estavel(locator, timeout=3)
            el = ultra_short_wait.until(EC.visibility_of_element_located(locator))
            if not _elemento_habilitado(el):
                time.sleep(0.05)
                continue
            actions.reset_actions()
            try:
                driver.execute_script(
                    "var e=arguments[0]; try {"
                    "e.dispatchEvent(new MouseEvent('mouseover',{bubbles:true,cancelable:true,view:window}));"
                    "e.dispatchEvent(new MouseEvent('mousemove',{bubbles:true,cancelable:true,view:window}));"
                    "e.dispatchEvent(new MouseEvent('mouseenter',{bubbles:true,cancelable:true,view:window}));"
                    "} catch(err){}", el)
            except Exception:
                ActionChains(driver, duration=10).move_to_element(el).pause(0.03).perform()
            return
        except (StaleElementReferenceException, ElementNotInteractableException) as e:
            ultimo_erro = e
            actions.reset_actions()
            time.sleep(0.05)
    raise ultimo_erro if ultimo_erro else RuntimeError(f"Falha hover_em em {locator}")

def aguardar_navegacao(anterior=None, timeout=12):
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
    aguardar_pagina_pronta(modo="normal", timeout=max(4, int(fim - time.time())))

def passo(titulo, fn, *args, modo_antes="leve", modo_depois="leve", **kwargs):
    print(f"{titulo} ...", flush=True)
    if modo_antes is not None:
        aguardar_pagina_pronta(modo=modo_antes)
    t0 = time.time()
    try:
        resultado = fn(*args, **kwargs)
    except Exception as e:
        dt = time.time() - t0
        print(f"{titulo} ({dt:.2f}s) → {type(e).__name__}: {e}", flush=True)
        raise
    if modo_depois is not None:
        aguardar_pagina_pronta(modo=modo_depois)
    dt = time.time() - t0
    print(f"{titulo} ({dt:.2f}s)", flush=True)
    return resultado

def preencher_login_rapido(locator, valor, sensivel=False):
    try:
        els = driver.find_elements(*locator)
        if els:
            el = els[0]
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "try { arguments[0].setAttribute('value', arguments[1]); } catch(e){}"
                "try { arguments[0].dispatchEvent(new Event('input', {bubbles:true})); } catch(e){}"
                "try { arguments[0].dispatchEvent(new Event('change', {bubbles:true})); } catch(e){}",
                el, valor
            )
            return
    except Exception:
        pass
    # fallback via querySelector no JS (busca feita no navegador = 1 roundtrip)
    sel = _locator_to_css(locator)
    if sel:
        try:
            driver.execute_script(
                "var el = document.querySelector(arguments[0]); if (el) { "
                "el.value = arguments[1]; try { el.setAttribute('value', arguments[1]); } catch(e){}"
                "try { el.dispatchEvent(new Event('input', {bubbles:true})); } catch(e){}"
                "try { el.dispatchEvent(new Event('change', {bubbles:true})); } catch(e){} }",
                sel, valor
            )
        except Exception:
            pass

def _locator_to_css(locator):
    import re
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
        if m: return f"{m.group(1)}[type='{m.group(2)}']"
    return None

def fechar_painel_selectcheckboxmenu(base_id, timeout=8):
    """Fecha painel de um SelectCheckboxMenu (ex: selectForm:variavel) com CONFIABILIDADE.
       - Early return: se o painel JÁ está fechado, retorna instantaneamente.
       - 4 estratégias para fechar:
         1) widget PrimeFaces.hide()
         2) clique fora no body (document.body.click())
         3) ESC via send_keys(body)
         4) remove display + seta display none no painel via JS
       - No final: espera invisibilidade ou absence do painel (no máximo timeout) + limpa overlays.
    """
    painel_sel = f"div[id='{base_id}_panel'].ui-selectcheckboxmenu-panel"
    # ------------------------------------------------------------------
    # Early return: painel já está fechado?
    # ------------------------------------------------------------------
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
        # Também aceita que o container não esteja "aberto"
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
        # Painel já fechado.
        try:
            aguardar_pagina_pronta(modo="instantaneo", timeout=3)
        except Exception:
            pass
        return True

    # ------------------------------------------------------------------
    # Fechamento em 4 estratégias (loop por rodadas)
    # ------------------------------------------------------------------
    fim_geral = time.time() + timeout
    fechou = False
    for rodada in range(3):
        if fechou or time.time() > fim_geral:
            break

        # 1) widget.hide() (mais limpo)
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
        if _fechado(): fechou = True; break
        # 2) clique fora no body
        try:
            driver.execute_script("try { document.body.click(); } catch(e){}")
        except Exception:
            pass
        time.sleep(0.05)
        if _fechado(): fechou = True; break
        # 3) ESC no body
        try:
            for b in driver.find_elements(By.TAG_NAME, "body")[:1]:
                try:
                    b.send_keys(Keys.ESCAPE)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(0.05)
        if _fechado(): fechou = True; break
        # 4) force-close via JS (último recurso)
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
            fechou = True; break
        time.sleep(0.08)

    # Espera final até o painel desaparecer completamente (até 4s)
    try:
        WebDriverWait(driver, 4, poll_frequency=0.05).until(
            lambda d: _fechado() or
                      (len(d.find_elements(By.CSS_SELECTOR, painel_sel)) == 0) or
                      (not d.find_element(By.CSS_SELECTOR, painel_sel).is_displayed())
        )
    except Exception:
        pass
    try:
        _limpar_overlays_orphans()
        aguardar_pagina_pronta(modo="instantaneo", timeout=5)
    except Exception:
        pass
    return _fechado()

def marcar_radiobutton_primefaces(table_id, value_alvo, label_table=None, timeout=10):
    """Marca um radiobutton group do PrimeFaces (table.ui-selectoneradio).
       Parâmetros:
         table_id: ex 'selectForm:tipoEstimativa' / 'selectForm:exibicao'
         value_alvo: ex '21' (Frequência), '22' (Difusão), 'true' (Valor), 'false' (Variação)
       Estratégias:
         1) Early return: já tem input:checked com esse value?
         2) Espera ATIVA até timeout para o input com value_alvo EXISTIR (evita falha 0.34s)
         3) Busca input[type=radio][name=table_id][value=<alvo>] → acha label for correspondente → clica
         4) Fallback: execute_script no input: seta checked = true + .click() + change + blur
         5) Final: valida que o checked realmente é value_alvo
    """
    fim_geral = time.time() + timeout
    value_alvo_str = str(value_alvo).strip()
    radio_name = table_id
    table_sel = f"table#{table_id}.ui-selectoneradio"
    input_sel = f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']"

    # =============================================================
    # PASSO 0 (NOVO e CRÍTICO): Espera ATIVA pelo INPUT com value_alvo
    #   - Antes de tentar marcar QUALQUER COISA, esperamos o radiobutton
    #     desejado aparecer no DOM. Usa o timeout COMPLETO da função!
    #   - Isso evita a falha em 0.34s que acontecia quando o input ainda
    #     não tinha sido renderizado pelo AJAX do Estrato.
    # =============================================================
    input_existe = False
    primeira_tentativa_wait = True
    while time.time() < fim_geral:
        # Primeiro verifica se já está checado (early return)
        try:
            els_chk = driver.find_elements(By.CSS_SELECTOR,
                                           f"input[type=radio][name='{radio_name}']:checked")
            for r in els_chk:
                try:
                    if (r.get_attribute("value") or "").strip() == value_alvo_str:
                        # Já está marcado → retorna imediatamente
                        try:
                            aguardar_pagina_pronta(modo="instantaneo", timeout=3)
                        except Exception:
                            pass
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        # Verifica se o input desejado existe
        try:
            if driver.find_elements(By.CSS_SELECTOR, input_sel):
                input_existe = True
                break
        except Exception:
            pass
        # Também espera pela table (caso não exista ainda)
        try:
            driver.find_elements(By.CSS_SELECTOR, table_sel)
        except Exception:
            pass
        # Limpa overlays órfãos a cada 0.5s
        try:
            if primeira_tentativa_wait or (int(time.time() * 2) % 2 == 0):
                _limpar_overlays_orphans()
                primeira_tentativa_wait = False
        except Exception:
            pass
        try:
            aguardar_pagina_pronta(modo="instantaneo", timeout=2)
        except Exception:
            pass
        time.sleep(0.08)

    # Se o input NÃO apareceu nem após espera completa → tentar de qualquer jeito
    # (pode ser que o componente use name diferente do table_id)
    if not input_existe:
        # Tentativa extra: buscar input com value_alvo independente do name
        try:
            candidate_inputs = driver.find_elements(By.CSS_SELECTOR,
                f"input[type=radio][value='{value_alvo_str}']")
            for inp in candidate_inputs:
                try:
                    n = (inp.get_attribute("name") or "").strip()
                    if n:
                        # Atualiza radio_name e input_sel com o name real
                        radio_name = n
                        input_sel = f"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']"
                        input_existe = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

    try:
        aguardar_pagina_pronta(modo="instantaneo", timeout=4)
    except Exception:
        pass

    def _checado_corretamente():
        try:
            els = driver.find_elements(By.CSS_SELECTOR,
                                       f"input[type=radio][name='{radio_name}']:checked")
            if not els:
                return False
            for r in els:
                try:
                    v = (r.get_attribute("value") or "").strip()
                    if v == value_alvo_str:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        # Fallback JS
        try:
            return bool(driver.execute_script(
                f"var rs = document.querySelectorAll(\"input[type=radio][name='{radio_name}']\");"
                f"for (var i=0;i<rs.length;i++){{"
                f"  if (rs[i].checked && (rs[i].value||'').trim()==='{value_alvo_str}') return true;"
                f"}}"
                f"return false;"
            ))
        except Exception:
            return False

    # Early return: já marcado corretamente
    if _checado_corretamente():
        try:
            aguardar_pagina_pronta(modo="instantaneo", timeout=3)
        except Exception:
            pass
        return True

    def _tentar_marcar():
        if _checado_corretamente():
            return True
        # 1) Encontra input com value_alvo, tenta clicar no label for dele
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, input_sel)
            for inp in inputs:
                inp_id = inp.get_attribute("id") or ""
                if inp_id:
                    # tenta o label
                    labs = driver.find_elements(By.CSS_SELECTOR, f"label[for='{inp_id}']")
                    for lab in labs:
                        try:
                            lab.click()
                            time.sleep(0.04)
                            if _checado_corretamente(): return True
                        except Exception:
                            try:
                                ActionChains(driver, duration=10).move_to_element(lab).pause(0.02).click().perform()
                                if _checado_corretamente(): return True
                            except Exception:
                                pass
                # fallback: clicar no pai radiobutton-box
                try:
                    pai = inp.find_element(By.XPATH,
                        "./following-sibling::div[contains(@class,'ui-radiobutton-box')][1]")
                    try: pai.click()
                    except Exception:
                        ActionChains(driver).move_to_element(pai).pause(0.02).click().perform()
                    time.sleep(0.04)
                    if _checado_corretamente(): return True
                except Exception:
                    pass
                # fallback: clicar no próprio input
                try:
                    driver.execute_script("try { arguments[0].click(); } catch(e){}", inp)
                    time.sleep(0.04)
                    if _checado_corretamente(): return True
                except Exception:
                    pass
        except Exception:
            pass
        # 2) Fallback JS universal
        try:
            ok_js = bool(driver.execute_script(
                f"var rs = document.querySelectorAll(\"input[type=radio][name='{radio_name}'][value='{value_alvo_str}']\");"
                f"if (!rs || rs.length===0) {{ "
                f"  // Tentativa extra: busca por value independente de name (caso name mude)"
                f"  rs = document.querySelectorAll(\"input[type=radio][value='{value_alvo_str}']\");"
                f"  if (!rs || rs.length===0) return false; "
                f"  var rr = rs[0]; if (rr.name) var n_rr = rr.name; else return false;"
                f"}};"
                f"var inp = rs[0]; var radioName = inp.name || '{radio_name}';"
                f"try {{"
                f"  // Uncheck todos os outros"
                f"  var all = document.querySelectorAll(\"input[type=radio][name=\" + JSON.stringify(radioName) + \"]\");"
                f"  for (var i=0;i<all.length;i++){{ try {{ all[i].checked = false; }} catch(e){{}}"
                f"    try {{ var box = all[i].parentElement.querySelector('.ui-radiobutton-box');"
                f"           if (box) {{ box.classList.remove('ui-state-active','ui-state-hover');"
                f"                         var icon = box.querySelector('.ui-radiobutton-icon');"
                f"                         if (icon) icon.classList.remove('ui-icon-bullet'); "
                f"                         if (icon) icon.classList.add('ui-icon-blank'); }}"
                f"    }} catch(e){{}}"
                f"  }}"
                f"  inp.checked = true;"
                f"  try {{"
                f"    var box = inp.parentElement.querySelector('.ui-radiobutton-box');"
                f"    if (box) {{ box.classList.add('ui-state-active'); box.classList.remove('ui-state-default');"
                f"                var icon = box.querySelector('.ui-radiobutton-icon'); "
                f"                if (icon) icon.classList.add('ui-icon-bullet'); "
                f"                if (icon) icon.classList.remove('ui-icon-blank'); }}"
                f"  }} catch(e){{}}"
                f"  try {{ inp.dispatchEvent(new Event('change',{{bubbles:true,cancelable:true}})); }} catch(e){{}}"
                f"  try {{ inp.dispatchEvent(new Event('input',{{bubbles:true,cancelable:true}})); }} catch(e){{}}"
                f"  try {{ inp.blur(); }} catch(e){{}}"
                f"  try {{ document.body.click(); }} catch(e){{}}"
                f"  return true;"
                f"}} catch(e){{ return false; }}"
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
            _limpar_overlays_orphans()
        except Exception:
            pass
        ok = _tentar_marcar()
        if ok:
            break
        try:
            aguardar_pagina_pronta(modo="instantaneo", timeout=3)
        except Exception:
            pass
        time.sleep(0.08)

    # Validação final
    if _checado_corretamente():
        try:
            aguardar_pagina_pronta(modo="instantaneo", timeout=4)
            _limpar_overlays_orphans()
        except Exception:
            pass
        return True

    # =============================================================
    # [DIAG] FALHOU: diagnóstico completo do grupo de radios.
    # Ajuda o usuário a identificar: (1) value errado, (2) name diferente,
    # (3) widget ainda não renderizado, (4) checked em outro valor.
    # =============================================================
    try:
        todos_radios = []
        # 1) Procura por name === table_id (default)
        rs1 = driver.find_elements(By.CSS_SELECTOR,
                                   f"input[type=radio][name='{table_id}']")
        for r in rs1: todos_radios.append(r)
        # 2) Procura por name === radio_name (se foi atualizado no fallback)
        if radio_name and radio_name != table_id:
            rs2 = driver.find_elements(By.CSS_SELECTOR,
                                       f"input[type=radio][name='{radio_name}']")
            seen_ids = set(id(x) for x in todos_radios)
            for r in rs2:
                if id(r) not in seen_ids:
                    todos_radios.append(r); seen_ids.add(id(r))
        # 3) Procura dentro da table por ID
        tbl_els = driver.find_elements(By.ID, table_id)
        for tbl in tbl_els:
            try:
                rs3 = tbl.find_elements(By.CSS_SELECTOR, "input[type=radio]")
                seen_ids = set(id(x) for x in todos_radios)
                for r in rs3:
                    if id(r) not in seen_ids:
                        todos_radios.append(r); seen_ids.add(id(r))
            except Exception:
                pass
        # 4) Fallback JS (pega QUALQUER radio do DOM, se nada foi achado)
        diag_vals = []
        for r in todos_radios:
            try:
                nm = (r.get_attribute("name") or "").strip()
                vl = (r.get_attribute("value") or "").strip()
                chk = r.is_selected()
                diag_vals.append(f"name='{nm}' value='{vl}' checked={chk}")
            except Exception:
                diag_vals.append("<erro leitura>")
        if not diag_vals:
            try:
                diag_vals_js = driver.execute_script(
                    "var all = document.querySelectorAll('input[type=radio]'); "
                    "var out = [];"
                    "for (var i=0;i<Math.min(all.length, 50);i++) {"
                    "  var r = all[i];"
                    "  out.push('name='+r.name+' value='+r.value+' ch='+r.checked);"
                    "}"
                    "return out.join(' | ') || '<nenhum radio no DOM>';")
                print(f"  [DIAG marcar_radio] Nenhum radio encontrado via Selenium. "
                      f"Lista JS (50 primeiros): {diag_vals_js}", flush=True)
            except Exception as e_js2:
                print(f"  [DIAG marcar_radio] Fallback JS errou: {type(e_js2).__name__}", flush=True)
        else:
            print(f"  [DIAG marcar_radio] Grupo '{table_id}' (alvo='{value_alvo_str}') → "
                  f"Radios encontrados: {len(diag_vals)}. Valores: {', '.join(diag_vals)}", flush=True)
            # Destaca qual está marcado atualmente
            for d in diag_vals:
                if "checked=True" in d:
                    print(f"  [DIAG marcar_radio] ⚠️  Radio ATUALMENTE marcado: {d} "
                          f"(precisa ser value='{value_alvo_str}')", flush=True)
                    break
    except Exception as e_diag:
        print(f"  [DIAG marcar_radio] Erro ao fazer diagnóstico: {type(e_diag).__name__}", flush=True)

    return False

def abrir_selectcheckboxmenu_primefaces(base_id, timeout_geral=22):
    """Abre dropdown SelectCheckboxMenu do PrimeFaces com CONFIABILIDADE.
       - base_id: ex. 'selectForm:variavel' (ID do container principal)
       - Não usa só clicar no container div (que falhou com 45s de timeout):
         usa TRIGGERS internos: label / corner-right / icon-triangle / focus / show() via widget.
       - Tenta até 3 rodadas de clique, alternando trigger com body.click para quebrar blockUI.
       - No final: limpeza overlays.
    """
    # ------------------------------------------------------------------
    # 0. Preparação: página pronta + overlays limpos
    # ------------------------------------------------------------------
    aguardar_pagina_pronta(modo="rapido")
    _limpar_overlays_orphans()

    # ------------------------------------------------------------------
    # 1. Detectar container + triggers internos
    # ------------------------------------------------------------------
    container_sel = f"div[id='{base_id}']"
    try:
        WebDriverWait(driver, 6, poll_frequency=0.05).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, container_sel))
        )
    except Exception:
        pass
    # Tentativa #0 por widget PrimeFaces (mais confiável quando existe)
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
        # Label do SelectCheckboxMenu (o label clicável com o texto padrão)
        f"{container_sel} a.ui-selectcheckboxmenu-label, "
        f"{container_sel} div.ui-selectcheckboxmenu-label-container a, "
        f"{container_sel} .ui-selectcheckboxmenu-label",
        # Botão de dropdown canto direito (ícone seta)
        f"{container_sel} a.ui-corner-right, {container_sel} a.ui-selectcheckboxmenu-trigger, "
        f"{container_sel} .ui-icon-triangle-1-s, {container_sel} span.ui-icon",
        # Label externo para o input (alguns casos)
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
                    _limpar_overlays_orphans()
                except Exception:
                    pass
                ultima_limpeza = agora
            # Tenta clique via navegador (JS) primeiro, evitando overlays de cima
            try:
                driver.execute_script(
                    f"var trig = document.querySelector(arguments[0]);"
                    f"if (!trig) return false;"
                    f"try {{ trig.scrollIntoView({{block:'center', inline:'center'}}); }} catch(e){{}}"
                    f"try {{ trig.focus(); }} catch(e){{}}"
                    f"try {{ trig.click(); return true; }} catch(e){{}}"
                    f"try {{ trig.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,cancelable:true,view:window}})); trig.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,cancelable:true,view:window}})); trig.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true,view:window}})); return true; }} catch(e2){{}}"
                    f"return false;",
                    trig_sel
                )
            except Exception:
                pass
            # Fallback: Selenium click direto
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
            # Espera até 1.5s por abertura após cada clique
            fim_mini = time.time() + 1.5
            while (not abriu) and time.time() < fim_mini:
                if _aberto():
                    abriu = True
                    break
                time.sleep(0.05)
            if not abriu:
                # Quebra blockUI que pode ter aparecido: click no body
                try:
                    driver.execute_script("try { document.body.click(); } catch(e){}")
                except Exception:
                    pass
                time.sleep(0.08)

    if not abriu:
        # TENTATIVA FINAL: se existe widget PrimeFaces (show)
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
            # Espera até 2s por abertura
            fim_mini = time.time() + 2.0
            while (not abriu) and time.time() < fim_mini:
                if _aberto():
                    abriu = True
                    break
                time.sleep(0.06)
        except Exception:
            pass

    # Garantias finais: se abriu, limpa overlays e espera o painel aparecer
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
        aguardar_pagina_pronta(modo="rapido", timeout=5)
        _limpar_overlays_orphans()
    return abriu

def _validar_campo_preenchido(locator, valor_esperado):
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        v = (els[0].get_attribute("value") or "").strip()
        return v == valor_esperado.strip()
    except Exception:
        return False

def _preencher_por_send_keys_direto(locator, valor, limpar=True):
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

def _preencher_por_js_com_events(locator, valor):
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
        # fallback via argumento de elemento
        els = driver.find_elements(*locator)
        if not els:
            return False
        return bool(driver.execute_script(
            "var el=arguments[0], v=arguments[1];"
            "try { el.focus(); el.value=''; el.value = v; el.setAttribute('value', v);"
            "el.dispatchEvent(new Event('input',{bubbles:true}));"
            "el.dispatchEvent(new Event('change',{bubbles:true})); el.blur(); return true; }"
            "catch(e){ return false; }",
            els[0], valor
        ))
    except Exception:
        return False

def _preencher_por_action_chains(locator, valor):
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        el = els[0]
        actions = ActionChains(driver, duration=10)
        try:
            actions.move_to_element(el).pause(0.02).click().pause(0.02)
            actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).pause(0.02)
            actions.send_keys(Keys.DELETE).pause(0.02)
            actions.send_keys(valor).pause(0.03)
            actions.perform()
            return True
        except Exception:
            try:
                actions.reset_actions()
            except Exception:
                pass
            return False
    except Exception:
        return False

def fazer_login_turbo(usuario, senha, timeout_submit=25):
    """Login CONFIÁVEL e rápido.
       - Preenchimento com 3 estratégias em cascata (send_keys nativo / JS c/ events / ActionChains).
       - Valida ambos os campos com get_attribute('value') antes de submeter.
       - Até 2 tentativas totais de preenchimento.
    """
    loc_usr = (By.CSS_SELECTOR,
               "#loginForm\\:formLogin_usuarioInput, input[type='text'], input[id*='username' i], input[id*='login' i]")
    loc_pwd = (By.CSS_SELECTOR,
               "#loginForm\\:formLogin_senhaInput, input[type='password']")

    # ------------------------------------------------------------------
    # Etapa 0: garante DOM pronto
    # ------------------------------------------------------------------
    try:
        WebDriverWait(driver, 4, poll_frequency=0.05).until(
            lambda d: (len(d.find_elements(*loc_pwd)) > 0
                       or len(d.find_elements((By.CSS_SELECTOR, "input[type='password']"))) > 0)
        )
    except Exception:
        pass
    try:
        _limpar_overlays_orphans()
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Etapa 1: PREENCHER (2 rodadas com 3 estratégias cada)
    # ------------------------------------------------------------------
    usr_ok = False
    pwd_ok = False
    estrategias = [
        ("Selenium send_keys",
         lambda: _preencher_por_send_keys_direto(loc_usr, usuario)
                 and _preencher_por_send_keys_direto(loc_pwd, senha)),
        ("JS com eventos input/change",
         lambda: _preencher_por_js_com_events(loc_usr, usuario)
                 and _preencher_por_js_com_events(loc_pwd, senha)),
        ("ActionChains sequencial",
         lambda: _preencher_por_action_chains(loc_usr, usuario)
                 and _preencher_por_action_chains(loc_pwd, senha)),
    ]

    for rodada in range(2):
        for nome, fn in estrategias:
            try:
                ok = fn()
            except Exception:
                ok = False
            usr_ok = _validar_campo_preenchido(loc_usr, usuario)
            pwd_ok = _validar_campo_preenchido(loc_pwd, senha)
            if usr_ok and pwd_ok:
                break
            time.sleep(0.05)
        if usr_ok and pwd_ok:
            break
        time.sleep(0.08)

    if not usr_ok:
        print(f"Campo usuário NÃO foi preenchido após 2 rodadas (esperado='{usuario[:2]}***').", flush=True)
    if not pwd_ok:
        print("Campo senha NÃO foi preenchido após 2 rodadas.", flush=True)

    # ------------------------------------------------------------------
    # Etapa 2: SUBMIT com 2 tentativas
    # ------------------------------------------------------------------
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
                if _pegou_erro_login()[0]:
                    break
                try:
                    if (driver.current_url or "") != url_antes:
                        break
                except Exception:
                    pass
                time.sleep(0.03)
            if _pegou_erro_login()[0]:
                break
            try:
                if (driver.current_url or "") != url_antes:
                    break
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Etapa 3: Detectar sucesso ou falha
    # ------------------------------------------------------------------
    fim = time.time() + timeout_submit
    ultima_limpeza = 0.0
    logou = False
    erro_msg = ""
    while time.time() < fim:
        agora = time.time()
        if agora - ultima_limpeza > 2.0:
            try:
                _limpar_overlays_orphans()
            except Exception:
                pass
            ultima_limpeza = agora
        tem_erro, txt_erro = _pegou_erro_login()
        if tem_erro:
            erro_msg = txt_erro or "(mensagem de erro detectada)"
            break
        try:
            if (driver.current_url or "") != url_antes:
                logou = True
                break
        except Exception:
            pass
        if not _na_tela_login():
            logou = True
            break
        time.sleep(0.05)

    if not logou and not erro_msg:
        restante = max(3, int(fim - time.time()))
        aguardar_pagina_pronta(modo="navegacao", timeout=restante)
        try:
            _limpar_overlays_orphans()
        except Exception:
            pass
        if not _na_tela_login():
            logou = True
        try:
            if (driver.current_url or "") != url_antes:
                logou = True
        except Exception:
            pass

    if erro_msg:
        print(f"Erro de login detectado: {erro_msg[:200]}", flush=True)
    return logou, erro_msg

def preencher_texto_simples(locator, valor, sensivel=False):
    for i in range(3):
        esperar_estavel(locator, timeout=3)
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
                el, valor)
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

def _ajustar_checkboxes_js(base_id, modo="todas", valores_desejados=None, labels_preferidas=None):
    """
    AJUSTA CHECKBOXES DE UM SelectCheckboxMenu EM LOTE VIA JS (0.01s TOTAL!).
    NÃO usa clicar_com_retry por checkbox (que gastava 0.3s+ por item!).

    Parâmetros:
      base_id: ex "selectForm:extrato" / "selectForm:variavel"
      modo: "todas"          → marca TODAS as opções (desmarca nenhuma)
            "preferencia"    → tenta labels_preferidas, se nenhuma achar marca TODAS
            "lista_valores"  → marca só os que têm value em valores_desejados, DESMARCA os outros
      valores_desejados: lista de values dos checkboxes para manter marcados (modo "lista_valores")
      labels_preferidas: lista lowercase de labels preferenciais (modo "preferencia")
    Retorna: qtd_checkboxes_marcados_ao_final (int)
    """
    panel_sel = f"div[id='{base_id}_panel']"
    valores_js = str([str(x) for x in (valores_desejados or [])])
    labels_js = str([str(x).lower() for x in (labels_preferidas or [])])

    script = f"""
    var modo = "{modo}";
    var valores = {valores_js};
    var labelsPref = {labels_js};
    var todos = document.querySelectorAll("{panel_sel} input[type='checkbox']");
    var marcados = 0;
    var marcouPreferida = false;

    // PASSO 1 (todos os modos): se for modo "lista_valores" → sincroniza checked com valores[]
    if (modo === "lista_valores") {{
      for (var i=0; i<todos.length; i++) {{
        var cb = todos[i];
        var v = (cb.value || "").trim();
        var deve = valores.indexOf(v) >= 0;
        if (cb.checked !== deve) {{
          try {{ cb.click(); }} catch(e){{ try {{ cb.checked = deve; }} catch(e2){{}} }}
          try {{
            var box = (cb.parentElement || cb.parentNode).querySelector(".ui-chkbox-box");
            if (box) {{
              if (deve) {{ box.classList.add("ui-state-active","ui-state-hover");
                var ic = box.querySelector(".ui-chkbox-icon");
                if (ic) {{ ic.classList.remove("ui-icon-blank"); ic.classList.add("ui-icon-check"); }}
              }} else {{ box.classList.remove("ui-state-active","ui-state-hover");
                var ic2 = box.querySelector(".ui-chkbox-icon");
                if (ic2) {{ ic2.classList.add("ui-icon-blank"); ic2.classList.remove("ui-icon-check"); }}
              }}
            }}
          }} catch(e){{}}
        }}
        if (cb.checked) marcados++;
      }}
      return marcados;
    }}

    // PASSO 1 (preferencia/todas): PRIMEIRO desmarca TUDO que está marcado
    for (var i=0; i<todos.length; i++) {{
      var cb = todos[i];
      if (cb.checked) {{
        try {{ cb.click(); }} catch(e){{ try {{ cb.checked = false; }} catch(e2){{}} }}
        try {{
          var box = (cb.parentElement || cb.parentNode).querySelector(".ui-chkbox-box");
          if (box) {{ box.classList.remove("ui-state-active","ui-state-hover");
            var ic = box.querySelector(".ui-chkbox-icon");
            if (ic) {{ ic.classList.add("ui-icon-blank"); ic.classList.remove("ui-icon-check"); }}
          }}
        }} catch(e){{}}
      }}
    }}

    // PASSO 2 (modo preferencia): tenta encontrar label preferida
    if (modo === "preferencia") {{
      var labels = document.querySelectorAll("{panel_sel} label");
      for (var i=0; i<labels.length; i++) {{
        var lab = labels[i];
        var tx = ((lab.innerText || lab.textContent) || "").trim().toLowerCase();
        if (!tx) continue;
        if (labelsPref.indexOf(tx) >= 0) {{
          var labfor = lab.getAttribute("for");
          var cbAlvo = labfor ? document.getElementById(labfor) : null;
          if (!cbAlvo) {{
            // fallback: procura checkbox irmão anterior/sucessor do label
            var sib = lab.previousElementSibling;
            while (sib && !cbAlvo) {{
              if (sib.tagName && sib.tagName.toLowerCase() === "input" && sib.type === "checkbox") {{ cbAlvo = sib; break; }}
              sib = sib.previousElementSibling;
            }}
          }}
          if (cbAlvo && !cbAlvo.checked) {{
            try {{ cbAlvo.click(); }} catch(e){{ try {{ cbAlvo.checked = true; }} catch(e2){{}} }}
            try {{
              var bx = (cbAlvo.parentElement || cbAlvo.parentNode).querySelector(".ui-chkbox-box");
              if (bx) {{ bx.classList.add("ui-state-active","ui-state-hover");
                var ii = bx.querySelector(".ui-chkbox-icon");
                if (ii) {{ ii.classList.remove("ui-icon-blank"); ii.classList.add("ui-icon-check"); }}
              }}
            }} catch(e){{}}
            marcouPreferida = true;
            marcados++;
          }}
        }}
      }}
      if (marcouPreferida) {{
        // conta total marcados no final
        marcados = 0;
        for (var j=0; j<todos.length; j++) {{ if (todos[j].checked) marcados++; }}
        return marcados;
      }}
      // NÃO achou preferida → cai para o modo "todas" abaixo
    }}

    // PASSO 2 (modo "todas" OU preferencia sem match): MARCA TODAS as opções visíveis
    for (var i=0; i<todos.length; i++) {{
      var cb = todos[i];
      if (!cb.checked) {{
        try {{ cb.click(); }} catch(e){{ try {{ cb.checked = true; }} catch(e2){{}} }}
        try {{
          var bx = (cb.parentElement || cb.parentNode).querySelector(".ui-chkbox-box");
          if (bx) {{ bx.classList.add("ui-state-active","ui-state-hover");
            var ii = bx.querySelector(".ui-chkbox-icon");
            if (ii) {{ ii.classList.remove("ui-icon-blank"); ii.classList.add("ui-icon-check"); }}
          }}
        }} catch(e){{}}
      }}
      marcados++;
    }}
    return marcados;
    """
    try:
        res = driver.execute_script(script)
        try:
            driver.execute_script("try { document.body.click(); } catch(e){}")
        except Exception:
            pass
        return int(res) if res is not None else 0
    except Exception as e:
        return 0

def _checar_mensagem_obrigatorio():
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

def selecionar_valor(locator, valor, tipo="select"):
    """Preenche SelectOneMenu (tipo="select") OU Spinner/Ano (tipo="text") OU
       SelectOneMenu com trigger hidden (tipo="select") com label + click no corner-right.

       ATUALIZAÇÃO 2026-09-15 (evita 56s em mesInicio):
         - PRIMEIRO PASSO AGORA: JS <select>.value === valor (early return 0 AJAX)
         - SÓ chama tentar_por_trigger_e_options SE o valor estiver DIFERENTE.
         - Motivo: imagens 2/3 mostram <option value=""></option> VAZIO no topo + selected="selected" no Junho(5).
           Selenium Select.first_selected_option às vezes pegava o vazio e re-abria o menu à toa.
    """
    if tipo == "select":
        # ------------------------------------------------------------------
        # EARLY RETURN 0 (JS RÁPIDO ~0.005s): valor já correto?
        #   Se sim → retorna imediatamente, NÃO abre trigger, NÃO faz AJAX.
        # ------------------------------------------------------------------
        try:
            els_er = driver.find_elements(*locator)
            if els_er:
                el_er = els_er[0]
                if el_er.tag_name.lower() == "select":
                    v_er = driver.execute_script(
                        "var s = arguments[0];"
                        "try { var v = (s.value || '').trim(); if (v !== '') return v; } catch(e){};"
                        "try { var idx = s.selectedIndex; if (idx >= 0 && s.options[idx]) return (s.options[idx].value || '').trim(); } catch(e2){};"
                        "return '';", el_er) or ""
                    if str(v_er).strip() == str(valor).strip():
                        return  # ← PULA TUDO, 0 tempo!
        except Exception:
            pass

        # Tentativa 0 (agora só se valor DIFERENTE): SelectOneMenu via Click + Options
        try:
            tentar_por_trigger_e_options(locator, valor)
        except Exception:
            pass
        # Tentativa 1: usando Select(el) direto no hidden (funciona em alguns casos)
        for i in range(3):
            try:
                els = driver.find_elements(*locator)
                if not els:
                    time.sleep(0.05); continue
                el = els[0]
                if el.tag_name and el.tag_name.lower() == "select":
                    try:
                        Select(el).select_by_value(valor)
                        aguardar_ajax()
                        try:
                            sel_el = driver.find_element(*locator)
                            val_ok = driver.execute_script(
                                "var s=arguments[0]; try { var v=(s.value||'').trim(); if (v!=='') return v; } catch(e){};"
                                "try { var idx=s.selectedIndex; if (idx>=0 && s.options[idx]) return (s.options[idx].value||'').trim(); } catch(e2){};"
                                "return '';", sel_el) or ""
                            if val_ok.strip() == str(valor).strip():
                                return
                        except Exception:
                            pass
                    except Exception:
                        pass
            except StaleElementReferenceException:
                time.sleep(0.05); continue
            except Exception:
                time.sleep(0.05); continue
        raise RuntimeError(f"Falha ao selecionar valor '{valor}' em {locator}")
    elif tipo == "text":
        # Campo de texto (Ano=spinner) ou inputs de texto
        for i in range(6):
            aguardar_pagina_pronta(modo="instantaneo", timeout=3)
            try:
                els = driver.find_elements(*locator)
                if not els:
                    time.sleep(0.08); continue
                el = els[0]
                if not _elemento_habilitado(el):
                    time.sleep(0.12); continue
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
                        el, valor
                    )
                except Exception:
                    pass
                aguardar_ajax()
                # Fallback final: Selenium
                try:
                    el.click()
                    time.sleep(0.015)
                    el.send_keys(Keys.CONTROL, "a")
                    time.sleep(0.008)
                    el.send_keys(Keys.DELETE)
                    time.sleep(0.008)
                    el.send_keys(valor)
                    driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change',{bubbles:true})); arguments[0].blur(); try { document.body.click(); } catch(e){}",
                        el
                    )
                except (StaleElementReferenceException, ElementNotInteractableException):
                    pass
                aguardar_ajax()
                ok = False
                for _ in range(6):
                    try:
                        els2 = driver.find_elements(*locator)
                        if els2:
                            vnow = (els2[0].get_attribute("value") or "").strip()
                            if vnow == str(valor).strip():
                                ok = True; break
                    except Exception:
                        pass
                    time.sleep(0.08)
                if ok:
                    return
                if _checar_mensagem_obrigatorio():
                    time.sleep(0.15); continue
            except (StaleElementReferenceException, ElementNotInteractableException):
                time.sleep(0.12)
        raise RuntimeError(f"Falha ao preencher campo {locator} com valor '{valor}'")
    raise RuntimeError(f"tipo desconhecido {tipo}")

def valor_campo_jah_correto(locator, valor_esperado, tipo="select"):
    """Retorna True se o campo já tem o valor correto → evita fazer clique/AJAX desnecessário.

       MÉTODO PREFERENCIAL (evita bugs): usa JS nativo DOM sobre Selenium .first_selected_option,
       pois o PrimeFaces renderiza <option value=""></option> VAZIO no topo dos selects,
       e Selenium às vezes retorna esse option vazio como first_selected_option = ERRADO!
    """
    try:
        els = driver.find_elements(*locator)
        if not els:
            return False
        el = els[0]
        if tipo == "select":
            try:
                if el.tag_name.lower() == "select":
                    # JS nativo: <select>.value sempre retorna o valor selecionado CORRETO.
                    # Se for "" tenta também o selectedIndex para cobrir raros casos.
                    cur_js = driver.execute_script(
                        "var s = arguments[0];"
                        "try { var v = (s.value || '').trim(); if (v !== '') return v; } catch(e){};"
                        "try { var idx = s.selectedIndex; if (idx >= 0 && s.options[idx]) return (s.options[idx].value || '').trim(); } catch(e2){};"
                        "return '';", el) or ""
                    if str(cur_js).strip() == str(valor_esperado).strip():
                        return True
                else:
                    # Talvez seja container, tente buscar o select child/hidden do mesmo id
                    eid = el.get_attribute("id") or ""
                    if eid:
                        sel_id = eid if eid.endswith("_input") else eid + "_input"
                        sels = driver.find_elements(By.ID, sel_id)
                        if sels and sels[0].tag_name.lower() == "select":
                            cur_js = driver.execute_script(
                                "var s = arguments[0];"
                                "try { var v = (s.value || '').trim(); if (v !== '') return v; } catch(e){};"
                                "try { var idx = s.selectedIndex; if (idx >= 0 && s.options[idx]) return (s.options[idx].value || '').trim(); } catch(e2){};"
                                "return '';", sels[0]) or ""
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

def tentar_por_trigger_e_options(locator_select_hidden, valor_option):
    """PARA SelectOneMenu do PrimeFaces (com <select aria-hidden='true'>:
       - clica no trigger (ui-selectonemenu-trigger) do componente para abrir o painel
       - encontra a option com o `value` correspondente no panel (li / div)
       - ou clica
       - espera item painel fica invisível (invisibility of panel)
       locator_select_hidden: o CSS selector do <select id='..._input'>
    """
    sel_id = None
    try:
        sel_el = driver.find_element(*locator_select_hidden)
        sel_id = sel_el.get_attribute("id") or ""
    except Exception:
        return False
    if not sel_id:
        return False

    # ------------------------------------------------------------------
    # EARLY RETURN: se o valor JÁ ESTÁ selecionado, não faz NADA
    # → evita abrir trigger + AJAX desnecessariamente!
    #   Usa JS nativo DOM select.value (NÃO usa Selenium Select.first_selected_option = bug option vazio no topo!)
    # ------------------------------------------------------------------
    try:
        cur_js = driver.execute_script(
            "var s=arguments[0]; try { var v=(s.value||'').trim(); if (v!=='') return v; } catch(e){};"
            "try { var idx=s.selectedIndex; if (idx>=0 && s.options[idx]) return (s.options[idx].value||'').trim(); } catch(e2){};"
            "return '';", sel_el) or ""
        if cur_js.strip() == str(valor_option).strip():
            return True
    except Exception:
        pass
    # ex: sel_id = 'selectForm:mesInicio_input'
    base = sel_id[:-6] if sel_id.endswith("_input") else sel_id
    trigger_sel = f"div[id='{base}'] div.ui-selectonemenu-trigger, div[id='{base}'] a.ui-corner-right, div[id='{base}'] div.ui-selectonemenu-label-container"
    panel_sel = f"div[id='{base}_panel'].ui-selectonemenu-panel, div[id='{base}_items'].ui-selectonemenu-items, div[id='{base}_content']"
    option_sel = (f"div[id='{base}_panel'] li[data-label],div[id='{base}_panel'] div.ui-selectonemenu-item, "
                 f"div[id='{base}_items'] div[data-label], li[data-label], ul.ui-selectonemenu-items li")

    # Tenta abrir pelo widget primeiro
    try:
        driver.execute_script(
            f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
            f" var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base}') : null;"
            f" if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
            f"  var x = PrimeFaces.widgets[k]; if(x && x.id==='{base}') w = x; }});"
            f" if (w && typeof w.show === 'function') {{ try {{ w.show(); return true; }} }} }}"
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
        return False

    abriu = _aberto()
    for rodada in range(3):
        if abriu:
            break
        # Clica trigger JS
        try:
            driver.execute_script(
                "var t = document.querySelector(arguments[0]);"
                "if (!t) return false;"
                "try { t.scrollIntoView({block:'center'}); } catch(e){}"
                "try { t.focus(); } catch(e){}"
                "try { t.click(); return true; } catch(e){}"
                "try { t.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));"
                "t.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));"
                "t.dispatchEvent(new MouseEvent('click',{bubbles:true})); return true; } catch(e2){}"
                "return false;",
                trigger_sel
            )
        except Exception:
            pass
        # Fallback Selenium
        try:
            for t in driver.find_elements(By.CSS_SELECTOR, trigger_sel)[:1]:
                try: t.click()
                except Exception:
                    try: ActionChains(driver).move_to_element(t).pause(0.01).click().perform()
                    except Exception: pass
        except Exception:
            pass
        # Espera 1.2s
        fim_mini = time.time() + 1.2
        while (not abriu) and time.time() < fim_mini:
            if _aberto():
                abriu = True
                break
            time.sleep(0.04)
        if not abriu:
            try:
                driver.execute_script("try { document.body.click(); } catch(e){}")
            except Exception:
                pass
            time.sleep(0.06)

    if not abriu:
        return False

    # Tenta encontrar opção pelo value no <select hidden> (texto da option)
    label_alvo = None
    try:
        for opt in Select(driver.find_element(*locator_select_hidden)).options:
            try:
                if (opt.get_attribute("value") or "").strip() == str(valor_option).strip():
                    label_alvo = (opt.text or "").strip()
                    break
            except Exception:
                continue
    except Exception:
        label_alvo = None

    def _clica_opcao_label():
        if not label_alvo:
            return False
        try:
            # Busca li/div no painel com texto exato da label_alvo OU data-label=label_alvo
            items = driver.find_elements(By.CSS_SELECTOR, option_sel)
            for it in items:
                try:
                    dl = (it.get_attribute("data-label") or "").strip()
                    tx = (it.text or "").strip()
                    if dl == label_alvo or tx == label_alvo:
                        try: it.click(); return True
                        except Exception:
                            ActionChains(driver).move_to_element(it).pause(0.01).click().perform(); return True
                except Exception:
                    pass
            # Fallback por execute_script
            try:
                return bool(driver.execute_script(
                    "var items = document.querySelectorAll(arguments[0]);"
                    "var lab = arguments[1];"
                    "for (var i=0;i<items.length;i++) {"
                    "  var it = items[i];"
                    "  var dl = it.getAttribute ? (it.getAttribute('data-label')||'').trim();"
                    "  var tx = (it.textContent||'').trim();"
                    "  if (dl===lab || tx===lab) {"
                    "    try { it.scrollIntoView({block:'center'}); it.click(); return true; } catch(e){} } } return false;",
                    option_sel, label_alvo
                ))
            except Exception:
                return False
        except Exception:
            return False

    ok_opcao = False
    for tent_op in range(3):
        if ok_opcao:
            break
        ok_opcao = _clica_opcao_label()
        if not ok_opcao:
            # Tenta via widget selectValue do PrimeFaces
            try:
                driver.execute_script(
                    f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
                    f" var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base}') : null;"
                    f" if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
                    f"  var x = PrimeFaces.widgets[k]; if(x && x.id==='{base}') w = x; }});"
                    f" if (w) {{ if (typeof w.selectValue === 'function') {{ try {{ w.selectValue('{valor_option}'); return true; }} catch(e){{}} }}"
                    f" if (typeof w.selectItem === 'function') {{ try {{ w.selectItem('{label_alvo or valor_option}'); return true; }} catch(e){{}} }}"
                    f"}} }} catch(e){{}} return false;"
                )
            except Exception:
                pass
        time.sleep(0.05)
        if ok_opcao:
            break
        time.sleep(0.05)

    if not ok_opcao:
        return False
    # Espera painel fechar
    try:
        WebDriverWait(driver, 4, poll_frequency=0.05).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, panel_sel)))
    except Exception:
        pass
    aguardar_pagina_pronta(modo="instantaneo", timeout=4)
    return True

# -------------------------------------------------------------
# FLUXO EXECUTÁVEL COMPLETO
# -------------------------------------------------------------
try:
    # -------------------------------------------------------------
    # PASSO 0: Detecção automática de página inicial carregada
    #   - SEM wrapper passo() aqui (overhead removido)
    #   - aguardar_tela_inicial() é suficiente: estrito + 0.5s janela
    # -------------------------------------------------------------
    print("[AUTO-DETECT] Aguardando carregamento completo da página inicial ...", flush=True)
    t0 = time.time()
    aguardar_tela_inicial()
    print(f"[AUTO-DETECT] Página inicial pronta em {time.time()-t0:.2f}s.\n", flush=True)

    # -------------------------------------------------------------
    # FASE 1: AUTENTICAÇÃO / LOGIN (TURBO — SEM waits de página entre campos)
    #   - Campos estáticos HTML, SEM AJAX, SEM máscara, SEM overlay
    #   - fazer_login_turbo() executa tudo em 1-2 execute_script + 1 única espera
    #   - NÃO usa wrapper passo() = 0 overhead
    # -------------------------------------------------------------
    print("===== FASE 1: Autenticação =====", flush=True)
    t0 = time.time()
    logou, msg_erro = fazer_login_turbo(SEU_USUARIO, SUA_SENHA)
    dur_login = time.time() - t0
    if logou:
        print(f"Usuário + senha + submit OK em {dur_login:.2f}s\n", flush=True)
    else:
        if msg_erro:
            print(f"Login NÃO foi efetuado em {dur_login:.2f}s → {msg_erro[:250]}", flush=True)
        else:
            print(f"Login NÃO confirmado em {dur_login:.2f}s — tentando continuar mesmo assim.\n", flush=True)

    # ------------------------------------------------------------------
    # FASE 1.2: Render pós-login
    #   - Primeiro LIMPA overlays órfãos (blockUI do login que pode ter sobrado)
    #   - Depois detecta se ainda está na tela de login — se sim, pede confirmação de credenciais
    #   - Só então espera o botão "Sondagem Industrial"
    # ------------------------------------------------------------------
    print("===== FASE 1.2: Render pós-login =====", flush=True)
    t0 = time.time()
    _limpar_overlays_orphans()
    try:
        _limpar_overlays_orphans()
    except Exception:
        pass
    # Dupla checagem: se ainda está na tela login, avisa
    if (not logou) and _na_tela_login():
        tem_erro, txt = _pegou_erro_login()
        if tem_erro:
            raise RuntimeError(f"Falha no login (ainda está na tela de login): {txt[:300]}")
    # Espera por pelo menos 12s: presença do menu OU sair da tela de login
    try:
        WebDriverWait(driver, 12).until(
            lambda d: (
                len(d.find_elements(By.XPATH, "//button[span[text()='Sondagem Industrial']]")) > 0
                or not _na_tela_login()
            )
        )
    except TimeoutException:
        # Força limpeza e espera mais 5s, se ainda falhar, deixa seguir
        _limpar_overlays_orphans()
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[span[text()='Sondagem Industrial']]"))
            )
        except TimeoutException:
            if _na_tela_login():
                raise RuntimeError(
                    "Falha: após 17s do login, ainda está na tela de login e 'Sondagem Industrial' não apareceu. "
                    "Verifique credenciais / conectividade."
                )
    aguardar_pagina_pronta(modo="navegacao", timeout=8)
    _limpar_overlays_orphans()
    fechar_popups_e_dialogos()
    print(f"Página pós-login pronta em {time.time()-t0:.2f}s\n", flush=True)

    # -------------------------------------------------------------
    # FASE 2: ÁRVORE DE NAVEGAÇÃO DOS MENUS (modo TURBO - sem waits pesados)
    # -------------------------------------------------------------
    print("\n===== FASE 2: Navegação pela árvore de menus =====")

    # Locators da FASE 2 extraídos do HTML REAL das imagens:
    #   - IDs ESTÁTICOS (mg11200, mg11202, mg11203) = Muito mais rápidos/confiáveis do que busca por text().
    loc_sondagem_ind = (By.XPATH,
        "//button[contains(@class,'buttonSelecaoPesquisa') and span[@class='ui-button-text ui-c'][.='Sondagem Industrial']]")
    loc_consultas = (By.CSS_SELECTOR, "li[id='menuForm:mg11200'] > a.ui-menuitem-link")
    loc_resultados = (By.CSS_SELECTOR, "li[id='menuForm:mg11202'] > a.ui-menuitem-link")
    loc_federacao = (By.CSS_SELECTOR, "li[id='menuForm:mg11203'] > a.ui-menuitem-link")
    # Locator PROXIMO do hover Federação = PRIMEIRO item filho do submenu (para garantir que submenu abriu)
    loc_proximo_submenu_federacao = (By.CSS_SELECTOR,
        "li[id='menuForm:mg11203'] ul.ui-menu-child > li")

    passo_clique_menu("Clicar em 'Sondagem Industrial'",
        lambda: clicar_com_retry(loc_sondagem_ind), depois_nav=False)
    passo_hover_menu("Hover em 'Consultas'",
        lambda: hover_em(loc_consultas),   locator_proximo=loc_resultados)
    passo_hover_menu("Hover em 'Resultados ou Índices'",
        lambda: hover_em(loc_resultados),  locator_proximo=loc_federacao)
    passo_hover_menu("Hover em 'Federação'",
        lambda: hover_em(loc_federacao),   locator_proximo=loc_proximo_submenu_federacao)

    # ------------------------------------------------------------------
    # CLIQUE em "Por Atividade": link de SUBMIT do menuForm com onclick=addSubmitParam.submit
    # Usa helper turbo (3 estratégias de localizar o link + 3 de clicar).
    # Se falhar, cai em fallback (clicar_com_retry no locator exato) e depois espera.
    # ------------------------------------------------------------------
    t0_pa = time.time()
    ok_pa = clicar_por_atividade_turbo(timeout_geral=22)
    dt_pa = time.time() - t0_pa
    if ok_pa:
        print(f"Clicar em 'Por Atividade' ({dt_pa:.2f}s)", flush=True)
    else:
        print(f"Turbo 'Por Atividade' falhou em {dt_pa:.2f}s → usando fallback...", flush=True)
        try:
            loc_pa_fallback = (By.XPATH,
                "//li[@id='menuForm:mg11203']//ul[contains(@class,'ui-menu-child')]"
                "//a[contains(@class,'ui-menuitem-link') and span[text()='Por Atividade']]")
            fallback_t0 = time.time()
            clicar_com_retry(loc_pa_fallback)
            print(f"Fallback Por Atividade OK ({time.time()-fallback_t0:.2f}s)", flush=True)
        except Exception as e:
            raise RuntimeError(
                f"Por Atividade: tanto o turbo quanto o fallback falharam em {dt_pa:.2f}s. "
                f"Detalhe: {type(e).__name__}"
            ) from e

    # Garantia: wait staleness do formulário menuForm (se ainda existir) → confirma submit foi processado
    try:
        menuForms = driver.find_elements(By.ID, "menuForm")
        if menuForms:
            try:
                WebDriverWait(driver, 6, poll_frequency=0.03).until(
                    EC.staleness_of(menuForms[0]))
            except Exception:
                pass
    except Exception:
        pass

    passo("Aguardar carregamento da tela de parâmetros", lambda: (
        wait.until(EC.presence_of_element_located(
            (By.ID, "selectForm:coorte_input"))),
        aguardar_pagina_pronta(modo="navegacao", timeout=6)
    ), modo_antes=None, modo_depois=None)

    # -------------------------------------------------------------
    # FASE 3: PREENCHIMENTO DOS FILTROS E VARIÁVEIS
    # -------------------------------------------------------------
    print("\n===== FASE 3: Preenchimento dos filtros =====")

    # Locators dos filtros (IDs exatos extraídos do HTML REAL das imagens):
    #   - By.ID em vez de By.CSS_SELECTOR pois IDs JSF têm ":" (pseudo-seletor CSS inválido)
    loc_coorte   = (By.ID, "selectForm:coorte_input")   # SelectOneMenu: values 634=Ceará, 688=Nordeste, 655=Brasil
    loc_mes_ini  = (By.ID, "selectForm:mesInicio_input") # SelectOneMenu: 0=Janeiro..11=Dezembro
    loc_ano_ini  = (By.ID, "selectForm:anoInicio_input")  # Spinner texto maxlength=4
    loc_mes_fim  = (By.ID, "selectForm:mesFim_input")    # SelectOneMenu: idem mesInicio
    loc_ano_fim  = (By.ID, "selectForm:anoFim_input")     # Spinner texto maxlength=4

    # -- Alias legíveis para cada filtro --
    #   Observação dos HTMLs REAIS das 9 imagens sobre ONCHANGE:
    #     - Coorte     -> onchange atualiza 12 componentes (inclui atividade, variavel, extrato, região...) → MODO DEPOIS = estrito!
    #     - mesInicio  -> onchange PrimeFaces.ab({... u:["selectForm:variavel"]}) → só atualiza variáveis → normal
    #     - anoInicio  -> onchange PrimeFaces.ab({... u:["selectForm:variavel"]}) → só atualiza variáveis → normal
    #     - mesFim     -> SEM ONCHANGE no HTML (select sem onchange attribute) → instantaneo
    #     - anoFim     -> SEM ONCHANGE no HTML (input sem onchange attribute) → instantaneo
    filtros = [
        ("Selecionar Coorte = Ceará (634)",            loc_coorte,  "634",  "select", "estrito"),
        ("Selecionar Mês Inicial = Junho (5)",          loc_mes_ini, "5",    "select", "normal"),
        ("Preencher Ano Inicial = 2026",                loc_ano_ini, "2026", "text",   "normal"),
        ("Selecionar Mês Final = Agosto (7)",           loc_mes_fim, "7",    "select", "instantaneo"),
        ("Preencher Ano Final = 2026",                  loc_ano_fim, "2026", "text",   "instantaneo"),
    ]

    for titulo, loc, valor, tipo, modo_depois in filtros:
        # PRIMEIRO: Verifica se o valor do campo já está CORRETO.
        # Se já estiver, pulamos TODO o preenchimento (zero AJAX desnecessário)
        if valor_campo_jah_correto(loc, valor, tipo=tipo):
            print(f"  ⏭  {titulo} → Já preenchido, pulado", flush=True)
            continue
        # Coorte: onchange faz UPDATE de ~15 componentes (atividade, variavel, extrato, regiao...) → precisa de espera MAIS LONGA no DEPOIS
        # Outros SelectOneMenu: normal; Spinner Ano: rapido
        passo(titulo,
              lambda loc=loc, valor=valor, tipo=tipo: selecionar_valor(loc, valor, tipo=tipo),
              modo_antes="navegacao",
              modo_depois=modo_depois)

    # -------------------------------------------------------------
    # FASE 3.2: ESTRATO (PREENCHER ANTES DE VARIÁVEIS E RADIOS!)
    #   - Usuário pediu: "as variaveis tem que ser preenchidas depois que preencher Estrato:"
    #   - MOTIVO DA ORDEM CONFIRMADO NAS IMAGENS: onchange do TipoEstimativa atualiza wrappers da Exibição;
    #     onchange do Coorte atualiza o widget do Estrato.
    #   ****************************************************************
    #   * IMAGEM 1 (HTML REAL) CONFIRMA: ESTRATO = SELECTCHECKBOXMENU (MULTISELECT!) *
    #   *  container div id=selectForm:extrato class=ui-selectcheckboxmenu-multiple   *
    #   *  wrapper span id=selectForm:extratoFilterInputGroup (FILHO TEM WIDGET!)      *
    #   *  NÃO É SelectOneMenu! (ordem trocada: SelectCheckboxMenu AGORA É PRIMEIRO)  *
    #   ****************************************************************
    # Ordem de detecção (confirmados por imagens):
    #   B (NOVA PRIMEIRA): div id=selectForm:extrato classe ui-selectcheckboxmenu → SelectCheckboxMenu
    #   C (NOVA SEGUNDA):   wrappers extratoFilter* VAZIOS? → Não, mas wrappers atividaFilter* / regiaoFilter* VAZIOS são de OUTROS campos opcionais!
    #   A: SelectOneMenu (fallback caso widget mude)
    # -------------------------------------------------------------
    print("\n===== FASE 3.2: Estrato (preencher antes de variáveis) =====")
    def _preencher_estrato():
        """Preenche o campo Estrato.

        CONFIRMADO VERBATIM NAS NOVAS 4 IMAGENS (HTML REAL DEVTOOLS):
          * Wrapper correto: span id=selectForm:extratoFilterInputGroup (COM widget filho!)
          * Container id=selectForm:extrato class=ui-selectcheckboxmenu-multiple ui-selectcheckboxmenu
          * É UM SelectCheckboxMenu (MULTISELECT!) — NÃO é SelectOneMenu!

        Wrappers VAZIOS (outros campos opcionais NÃO relacionados ao Estrato):
          * span id=selectForm:regiaoFilterLabelGroup / InputGroup → VAZIOS (Região não renderizada)
          * span id=selectForm:atividaFilterLabelGroup / InputGroup → VAZIOS (Atividade não renderizada, grafia com 'da')

        Ordem de detecção (estrita por imagem real):
          B (PRIMEIRA):  div id=selectForm:extrato classe ui-selectcheckboxmenu → SelectCheckboxMenu (CASO REAL!)
          B2 (SEGUNDA):  wrapper extratoFilterInputGroup tem filho widget ui-selectcheckboxmenu → idem acima
          A  (TERCEIRA): SelectOneMenu (fallback raro caso widget mude)
          C  (ÚLTIMA):   Widget não existe (só label) → skip opcional
        """
        base_id = "selectForm:extrato"
        preferencia_labels = ["todas", "geral", "total", "indústria geral",
                              "industria geral", "todas as empresas",
                              "todos os estratos", "todos"]

        # ------------------------------------------------------------------
        # TENTATIVA B (AGORA PRIMEIRA! Confirmado na imagem 1):
        #   Procura container base com classe ui-selectcheckboxmenu.
        #   Se achar → trata como SelectCheckboxMenu multiseleção.
        # ------------------------------------------------------------------
        els_base = driver.find_elements(By.ID, base_id)
        ui_scbmenu = [e for e in els_base
                      if "ui-selectcheckboxmenu" in (e.get_attribute("class") or "")]
        if not ui_scbmenu:
            # Fallback: olha DENTRO do extratoFilterInputGroup por um filho com id=base_id
            wrappers_inp = driver.find_elements(By.ID, "selectForm:extratoFilterInputGroup")
            for wrp in wrappers_inp:
                try:
                    filhos_widget = wrp.find_elements(By.CSS_SELECTOR,
                                                      "div.ui-selectcheckboxmenu")
                    for fw in filhos_widget:
                        fw_id = fw.get_attribute("id") or ""
                        if fw_id == base_id:
                            ui_scbmenu.append(fw)
                            els_base.append(fw)
                except Exception:
                    pass
        if ui_scbmenu:
            # ============================================================
            # FLUXO SELECTCHECKBOXMENU (igual a Variáveis):
            #   1) Abrir painel via helper abrir_selectcheckboxmenu_primefaces
            #   2) Ajustar TODOS os checkboxes VIA JS EM LOTE (0.01s total!)
            #      — NÃO usa mais clicar_com_retry por checkbox (gargalo 0.3s por item!)
            #   3) Valida ≥1 marcado
            #   4) Fecha painel via helper
            # ============================================================
            try:
                abriu_est = abrir_selectcheckboxmenu_primefaces(base_id, timeout_geral=12)
                if abriu_est:
                    try:
                        WebDriverWait(driver, 3, poll_frequency=0.03).until(
                            EC.visibility_of_element_located(
                                (By.ID, f"{base_id}_panel")))
                    except Exception:
                        pass

                    # AJUSTE VIA JS EM LOTE (0.01s):
                    #   Modo preferencia → tenta "Todas", "Geral", etc.
                    #   Se não achar → marca TODAS automaticamente.
                    qtd_checked_est = _ajustar_checkboxes_js(
                        base_id,
                        modo="preferencia",
                        labels_preferidas=preferencia_labels)

                    # Garantia: se JS retornou 0 (nenhum checkbox foi marcado),
                    # tenta modo "todas" para marcar pelo menos 1.
                    if qtd_checked_est < 1:
                        qtd_checked_est = _ajustar_checkboxes_js(base_id, modo="todas")

                    # 5) Fecha o painel
                    try:
                        fechou_est = fechar_painel_selectcheckboxmenu(base_id, timeout=6)
                        if not fechou_est:
                            try:
                                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            except Exception:
                                pass
                            try:
                                WebDriverWait(driver, 2, poll_frequency=0.03).until(
                                    EC.invisibility_of_element_located(
                                        (By.ID, f"{base_id}_panel")))
                            except Exception:
                                pass
                    except Exception:
                        pass
                return True
            except Exception as e_eb:
                print(f"Estrato SelectCheckboxMenu exceção: {type(e_eb).__name__}", flush=True)
                return False

        # ------------------------------------------------------------------
        # TENTATIVA A (TERCEIRA): SelectOneMenu (fallback raro caso widget mude)
        # ------------------------------------------------------------------
        sel_hidden = (By.ID, "selectForm:extrato_input")
        els = driver.find_elements(*sel_hidden)
        if els:
            try:
                opcoes = Select(els[0]).options
                valor_alvo = None
                for opt in opcoes:
                    try:
                        v = (opt.get_attribute("value") or "").strip()
                        tx = (opt.text or "").strip().lower()
                        if not v:
                            continue
                        if tx in preferencia_labels:
                            valor_alvo = v
                            break
                        if not valor_alvo:
                            valor_alvo = v
                    except Exception:
                        continue
                if valor_alvo is None:
                    return True
                ok = tentar_por_trigger_e_options(sel_hidden, valor_alvo)
                if ok:
                    return True
                try:
                    Select(els[0]).select_by_value(valor_alvo)
                    driver.execute_script(
                        f"try {{ if (window.PrimeFaces && PrimeFaces.widgets) {{"
                        f" var w = PrimeFaces.getWidgetById ? PrimeFaces.getWidgetById('{base_id}') : null;"
                        f" if (!w) Object.keys(PrimeFaces.widgets).forEach(function(k){{"
                        f"  var x = PrimeFaces.widgets[k]; if(x && x.id==='{base_id}') w = x; }});"
                        f" if (w && typeof w.selectValue === 'function') {{ try {{ w.selectValue('{valor_alvo}'); return true; }} }} }}"
                        f"}} catch(e){{}} return false;"
                    )
                except Exception:
                    pass
                try:
                    aguardar_pagina_pronta(modo="instantaneo", timeout=3)
                except Exception:
                    pass
                return True
            except Exception:
                pass

        # ------------------------------------------------------------------
        # TENTATIVA C (ÚLTIMA): Widget não existe (não renderizado) → skip opcional
        # ------------------------------------------------------------------
        label_count = len(driver.find_elements(By.CSS_SELECTOR, f"label[for='{base_id}']"))
        span_count = len(driver.find_elements(By.ID, "selectForm:extratoFilterInputGroup"))
        if label_count > 0 and span_count > 0:
            return True
        return True

    t0_est = time.time()
    est_ok = _preencher_estrato()
    dt_est = time.time() - t0_est
    if est_ok:
        # Detecta qual estratégia foi usada para imprimir status correto
        _tem_ui_scb = False
        try:
            for _e in driver.find_elements(By.ID, "selectForm:extrato"):
                if "ui-selectcheckboxmenu" in (_e.get_attribute("class") or ""):
                    _tem_ui_scb = True
        except Exception:
            pass
        if dt_est < 0.3:
            status_est = "não renderizado (opcional/spans vazios)"
        elif _tem_ui_scb:
            status_est = "SelectCheckboxMenu preenchido (multiseleção)"
        else:
            status_est = "ok"
        print(f"Preencher campo 'Estrato' ({status_est}) em {dt_est:.2f}s", flush=True)
    else:
        print(f"Campo 'Estrato' preenchimento falhou em {dt_est:.2f}s (continuando...)", flush=True)

    # ESPERA pós-Estrato: SOMENTE se houve preenchimento com AJAX.
    # Observação das imagens REAIS: 99% das vezes o campo estrato NÃO É RENDERIZADO (spans vazios).
    #   - Nesse caso, NÃO TEM AJAX → espera instantânea, não gasta 10s à toa.
    # Como saber se houve preenchimento real? → dt_est > 0.3s indica que entrou em tentar_por_trigger_e_options etc.
    print("Aguardando AJAX pós-Estrato (se existir)...", flush=True)
    if dt_est > 0.3:
        try:
            aguardar_pagina_pronta(modo="normal", timeout=6)
        except Exception:
            pass
    else:
        try:
            aguardar_pagina_pronta(modo="instantaneo", timeout=2)
        except Exception:
            pass
    try:
        # Garantir que widget de variáveis existe após re-render (senão falha depois)
        WebDriverWait(driver, 5, poll_frequency=0.03).until(
            EC.presence_of_element_located(
                (By.ID, "selectForm:variavel")))
    except Exception as e_wa:
        print(f"Widget Variáveis não apareceu após Estrato ({type(e_wa).__name__}) → tentando continuar...", flush=True)

    print("\n===== FASE 3.1: Variáveis (agora preenchidas DEPOIS de Estrato) =====")
    # Passo 3.1: Abrir menu SelectCheckboxMenu "Variáveis" (CONFIÁVEL)
    #   - 5 estratégias via abrir_selectcheckboxmenu_primefaces()
    #   - Máximo 12s, break por múltiplos detectores de estado aberto
    t0_var = time.time()
    abriu_vars = abrir_selectcheckboxmenu_primefaces("selectForm:variavel", timeout_geral=12)
    dt_var = time.time() - t0_var
    if abriu_vars:
        try:
            WebDriverWait(driver, 3, poll_frequency=0.03).until(
                EC.visibility_of_element_located(
                    (By.ID, "selectForm:variavel_panel")))
        except Exception:
            pass
        print(f"Abrir menu de Variáveis ({dt_var:.2f}s)", flush=True)
    else:
        print(f"Abrir menu de Variáveis falhou em {dt_var:.2f}s.", flush=True)
        raise RuntimeError(
            "Não consegui abrir o SelectCheckboxMenu de Variáveis (selectForm:variavel) após 12s. "
            "Pode ser: (1) o componente não carregou, "
            "(2) overlay/blockUI permaneceu no formulário, ou "
            "(3) o ID interno do componente foi alterado pelo servidor CNI."
        )
    # Completa o wrapper com waits do passo()
    try:
        aguardar_pagina_pronta(modo="leve", timeout=3)
    except Exception:
        pass

    # Mapeamento: Variáveis da UI (pelo VALUE do checkbox, não índice)
    #   Com base no HTML REAL das imagens:
    #   17  → p1t  - Margem de Lucro Operacional   → value="955"  (já marcado default)
    #   21  → p2t  - Situação Financeira da Empresa → value="956"  (já marcado default)
    #   23  → p3t  - Acesso ao Crédito da Empresa   → value="957"  (já marcado default)
    #   25  → p4t  - Preço médio matérias-primas    → value="958"  (já marcado default)
    #   Os campos default são 17,21,23,25 (marcados no HTML real).
    #   Caso queira marcar/demarcar adicionais, use a lista abaixo com os values:
    VAR_COD_POR_VALUE = {
        "955": "17",
        "956": "21",
        "957": "23",
        "958": "25",
        "52100": "0",   # coment - comentários
        "971": "1",     # COND - cond. atuais
        "953": "2",     # EXPEC - exp. atuais
        "972": "3",     # ICEI
        "53103": "4",   # IceiEst
        "53101": "5",   # IndCondEst
        "53102": "6",   # IndExpecEst
        "946": "7",     # PA - cond. economia
        "950": "8",     # PB - cond. setor
        "947": "9",     # PC - cond. empresa
        "943": "10",    # PD - exp. economia
        "951": "11",    # PE - exp. setor
        "949": "12",    # PF - exp. empresa
        "944": "13",    # PG - cond. estado
        "945": "14",    # PH - exp. estado
        "954": "15",    # pp - principais problemas 1
        "948": "16",    # (sem letra)
        "969": "18",    # p10 - quant. exportada
        "970": "19",    # p11 - intenção investimento 6m
        "961": "20",    # p2 - UCI efetiva
        "962": "22",    # p3 - utilização capacidade
        "963": "24",    # p4 - evolução num. empregados
        "965": "26",    # p5 - estoques planejados
        "966": "27",    # p6 - estoques evolução
        "964": "28",    # p7 - demanda
        "967": "29",    # p8 - núm. empregados
        "968": "30",    # p9 - compras mat prima
    }
    # Os desejados 17/21/23/25 mapeiam para values 955/956/957/958 (já estão marcados)
    variaveis_desejadas_cod = ["17", "21", "23", "25"]
    variaveis_desejadas_values = [v for (k, v) in VAR_COD_POR_VALUE.items()
                                  if k in [kk for kk, vv in VAR_COD_POR_VALUE.items()
                                           if vv in variaveis_desejadas_cod]]
    # Invert: cod → value
    def value_por_cod(cod):
        for val, c in VAR_COD_POR_VALUE.items():
            if c == cod:
                return val
        return None
    desejadas_values = [value_por_cod(c) for c in variaveis_desejadas_cod]
    desejadas_values = [x for x in desejadas_values if x]

    # ================================================================
    # OTIMIZAÇÃO TURBO (0.01s em vez de 5-10s!):
    #   NÃO usa mais 2 passos com clicar_com_retry em CADA checkbox
    #   (que gastava 0.3s+ wait por item).
    #   Agora usa 1 ÚNICA execute_script EM LOTE via _ajustar_checkboxes_js:
    #     → marca só os desejados, desmarca os outros.
    # ================================================================
    t_aj_var = time.time()
    qtd_marcadas = _ajustar_checkboxes_js(
        "selectForm:variavel",
        modo="lista_valores",
        valores_desejados=desejadas_values)
    dt_aj_var = time.time() - t_aj_var
    print(f"Ajustar checkboxes Variáveis (JS em lote) → "
          f"{qtd_marcadas} marcada(s) ({dt_aj_var:.3f}s)", flush=True)

    # Validação: confirmar que pelo menos 1 variável desejada está marcada
    val_qtd_ok = 0
    try:
        cbs = driver.find_elements(
            By.CSS_SELECTOR,
            "div.ui-selectcheckboxmenu-panel input[type='checkbox']:checked")
        for cb in cbs:
            v = (cb.get_attribute("value") or "").strip()
            if v in desejadas_values:
                val_qtd_ok += 1
        print(f"Variáveis desejadas marcadas: {val_qtd_ok}/{len(desejadas_values)}", flush=True)
    except Exception:
        pass
    if val_qtd_ok == 0 and qtd_marcadas < len(desejadas_values):
        print(f"Nenhuma variável desejada foi marcada! Tentando fallback JS...", flush=True)
        try:
            dv_js = str(desejadas_values)
            driver.execute_script(
                f"var vs = document.querySelectorAll(\"div.ui-selectcheckboxmenu-panel input[type=checkbox]\");"
                f"for (var i=0;i<vs.length;i++){{"
                f"  var v = (vs[i].value||'').trim();"
                f"  var des = {dv_js}.indexOf(v) >= 0;"
                f"  if (vs[i].checked !== des) {{"
                f"    try {{ vs[i].click(); }} catch(e){{ try {{ vs[i].checked = des; }} catch(e2){{}} }}"
                f"  }}"
                f"}};"
                f"try {{ document.body.click(); }} catch(e){{}} return true;"
            )
            time.sleep(0.05)
        except Exception as e_jv:
            print(f"Fallback JS variáveis falhou: {type(e_jv).__name__}", flush=True)

    # -------------------------------------------------------------
    # Fim FASE 3.1: Fechar painel SelectCheckboxMenu de Variáveis
    #   - Método novo: 4 estratégias (widget.hide() → body.click → ESC → force-close JS).
    #   - Early return se já fechou (não mais 57s de wait!)
    # -------------------------------------------------------------
    t_fecha = time.time()
    fechou = fechar_painel_selectcheckboxmenu("selectForm:variavel", timeout=10)
    dt_fecha = time.time() - t_fecha
    if fechou:
        print(f"Fechar painel de variáveis ({dt_fecha:.2f}s)", flush=True)
    else:
        print(f"Fechar painel de variáveis: helper falhou em {dt_fecha:.2f}s → fazendo wait...", flush=True)
        try:
            wait.until(EC.invisibility_of_element_located(
                (By.ID, "selectForm:variavel_panel")))
            print("Fechar painel de variáveis (wait OK)", flush=True)
        except Exception as e:
            print(f"Fechar painel de variáveis: wait falhou ({type(e).__name__}) → continuando...", flush=True)

    # ESPERA após variáveis: AJAX de marcação pode re-renderizar radios
    try:
        aguardar_pagina_pronta(modo="leve", timeout=4)
    except Exception:
        pass

    # -------------------------------------------------------------
    # Radio buttons: TipoEstimativa e Exibicao (AGORA DEPOIS DE TUDO!)
    #   - Agora usam marcar_radiobutton_primefaces(): não dependem de label[for=...]
    #     mas de input[type=radio][name=table_id][value='...'] + fallback JS completo.
    #   - TipoEstimativa: values = '21' (Frequência) / '22' (Difusão) (default: 22 Difusão)
    #   - Exibição: values = 'true' (Valor) / 'false' (Variação) (default: true Valor)
    # -------------------------------------------------------------
    print("\n===== FASE 3.3: Radio buttons (Tipo Estimativa + Exibição) =====")
    t0_te = time.time()
    te_ok = marcar_radiobutton_primefaces("selectForm:tipoEstimativa", "21", timeout=12)
    dt_te = time.time() - t0_te
    if te_ok:
        print(f"Marcar Tipo de Estimativa = Frequência ({dt_te:.2f}s)", flush=True)
    else:
        # Diagnóstico detalhado (ANTES do raise)
        print(f"Marcar Tipo de Estimativa falhou em {dt_te:.2f}s → Iniciando diagnóstico...", flush=True)
        try:
            # Primeiro procura a table por By.ID (evita InvalidSelectorException com ':')
            te_tbl_el = None
            te_tables = driver.find_elements(By.ID, "selectForm:tipoEstimativa")
            for t in te_tables:
                try:
                    if "ui-selectoneradio" in (t.get_attribute("class") or ""):
                        te_tbl_el = t
                        break
                except Exception:
                    pass
            te_table_existe = bool(te_tbl_el) or len(te_tables) > 0
            print(f"     [DIAG] table id=selectForm:tipoEstimativa EXISTE? {te_table_existe} (qtde: {len(te_tables)})", flush=True)
            te_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type=radio][name='selectForm:tipoEstimativa']")
            if not te_inputs:
                # Fallback: procura todos radios dentro da table (por ID)
                try:
                    if te_tbl_el:
                        te_inputs = te_tbl_el.find_elements(By.CSS_SELECTOR, "input[type=radio]")
                except Exception:
                    pass
            print(f"     [DIAG] inputs radios do grupo ENCONTRADOS: {len(te_inputs)}", flush=True)
            te_values = []
            for inp in te_inputs:
                try:
                    v = (inp.get_attribute("value") or "").strip()
                    chk = inp.is_selected()
                    te_values.append(f"{v} (checked={chk})")
                except Exception:
                    te_values.append("<erro>")
            if te_values:
                print(f"     [DIAG] Values dos radios ENCONTRADOS: {', '.join(te_values)}", flush=True)
            else:
                # Fallback JS para obter values
                try:
                    js_vals = driver.execute_script(
                        "var rs = document.querySelectorAll('input[type=radio][name=\"selectForm:tipoEstimativa\"]');"
                        "var out = []; for (var i=0;i<rs.length;i++) out.push((rs[i].value||'')+'(ch='+rs[i].checked+')'); return out.join(', ') || '<nenhum>';")
                    print(f"     [DIAG] Values via JS: {js_vals}", flush=True)
                except Exception as e_js:
                    print(f"     [DIAG] Erro JS: {type(e_js).__name__}", flush=True)
        except Exception as e_diag:
            print(f"     [DIAG] Erro no diagnóstico: {type(e_diag).__name__}", flush=True)
        raise RuntimeError(
            "Não consegui marcar Tipo de Estimativa = Frequência (value='21') após 12s. "
            "Veja [DIAG] acima no console. Causas prováveis: (1) Estrato ainda não terminou AJAX "
            "(esperar mais), (2) radiobutton Frequência NÃO EXISTE para os filtros selecionados "
            "(mudar Coorte/Atividade/Estrato), (3) value do radiobutton não é '21' — conferir DIAG "
            "acima para o value REAL do componente."
        )
    # Observação: Exibição default é Valor (true) → early return quase sempre não faz nada.
    t0_ex = time.time()
    ex_ok = marcar_radiobutton_primefaces("selectForm:exibicao", "true", timeout=10)
    dt_ex = time.time() - t0_ex
    if ex_ok:
        print(f"Marcar Exibição = Valor ({dt_ex:.2f}s)", flush=True)
    else:
        print(f"Marcar Exibição falhou em {dt_ex:.2f}s (continuando... Valor é o default)", flush=True)

    # -------------------------------------------------------------
    # FASE 3.4: ORIENTAÇÃO (NOVO CAMPO! confirmado imagem 3/4)
    #   HTML REAL: table id="selectForm:orientacao" class="ui-selectoneradio"
    #     - value="LINHA"  (label "Linha",  default checked="checked")  ← o que queremos
    #     - value="COLUNA" (label "Coluna")
    #   Sem onchange no input (AJAX não dispara). Default é LINHA (o que queremos).
    # -------------------------------------------------------------
    print("\n===== FASE 3.4: Radio button Orientação (Linha / Coluna) =====")
    t0_or = time.time()
    or_ok = marcar_radiobutton_primefaces("selectForm:orientacao", "LINHA", timeout=10)
    dt_or = time.time() - t0_or
    if or_ok:
        print(f"Marcar Orientação = Linha (LINHA) ({dt_or:.2f}s)", flush=True)
    else:
        print(f"Marcar Orientação falhou em {dt_or:.2f}s (continuando... Linha é o default checked)", flush=True)

    # -------------------------------------------------------------
    # FASE 4: PROCESSAMENTO E DOWNLOAD
    # -------------------------------------------------------------
    print("\n===== FASE 4: Processamento e Download =====")
    # Botão Pesquisar: ID ESTÁTICO confirmado na imagem 4!
    #   <button id="selectForm:pesquisar" name="selectForm:pesquisar"
    #     onclick="PrimeFaces.ab({s:'selectForm:pesquisar',p:'selectForm',u:'pesquisa'});return false;"
    passo("Clicar no botão 'Pesquisar'", lambda: clicar_com_retry(
        (By.ID, "selectForm:pesquisar")))

    passo("Aguardar renderização da tabela de índices", lambda: (
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR,
             "div[id='listDifusaoLinhaForm:indicesVariavelDataTable'].ui-datatable"))),
        aguardar_pagina_pronta(janela_estavel=1.0)
    ))

    # Botão Exportar extraído do HTML REAL da imagem (ID estático):
    #   a id='listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140'
    #   title='Exportar resultados para um arquivo de planilha do Excel'
    # Com fallback por CSS selector + title (para caso j_idt mude).
    passo("Clicar em 'Exportar para excel'", lambda: clicar_com_retry(
        (By.CSS_SELECTOR,
         "a[id='listDifusaoLinhaForm:indicesVariavelDataTable:j_idt140'],"
         "a[title='Exportar resultados para um arquivo de planilha do Excel'],"
         "a.ui-commandlink")))

    print("\n===== SUCESSO =====")
    print("Automação concluída. Aguardando finalizar download do arquivo Excel...")
    time.sleep(3)

finally:
    try:
        driver.quit()
    except Exception:
        pass
