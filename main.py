r"""
Entry point REFINADO da automação CNI — Pesquisas Conjunturais Industriais.

Refatoração arquitetural Clean Architecture + POM:
  ~2900 linhas monólito → 7 camadas (config / core / domain / infra / pages / services / main).

ARQUITETURA (NÃO ALTERAR — SOLID + Injeção de Dependência):
  config        → settings (Pydantic BaseSettings .env) + constants (100% extraídas do monólito)
  core          → hierarquia AppError + @with_retry (exponential backoff + jitter)
  domain        → PesquisaParams frozen Pydantic + validators + VAR_COD_POR_VALUE mappings
  infrastructure→ browser driver / waits (6 perfis ajax+hash+overlay) / actions (helpers JS intactos)
  pages (POM)   → LoginPage + MenuPage + ParametrosPage + ResultadosPage (locators privados By.ID)
  services      → AuthService (F1) + NavigationService (F2) + PesquisaService (F3+F4) + @with_retry ≥3
  main (aqui)   → entry point FINO < 200 linhas, NENHUM estado global, try/finally SEMPRE teardown.

AC-3 fail fast: get_settings() já no topo do main levanta ValidationError ANTES de abrir navegador
                se CNI_USER/CNI_PASSWORD ausentes no g:\ic\.env (template em .env.example).
                Usuário deve criar .env com credenciais VÁLIDAS (erro "usuário não encontrado"
                no login NÃO é bug código = credencial federação CNI recusada).

SEGURANÇA (6 pilares integrados):
  SEG-1: execute_script com arguments[0..N] em todo JS injetado (nenhuma concatenação Python→JS).
  SEG-2: URL whitelist assertiva após navegações críticas (apenas pesquisasconjunturais.cni.com.br).
  SEG-3: Watchdog global timeout (padrão 60min) com warning aos 5min restantes.
  SEG-4: Sanitização de logs (senhas/tokens substituídos por ***).
  SEG-5: Validação permissões .env ao carregar (world-readable → WARNING).
  SEG-6: Lock single-instance (.pipeline.lock) — só 1 execução por vez.
"""
from __future__ import annotations

import time
from pathlib import Path

from config.settings import get_settings
from config.constants import (
    URL_BASE_LOGIN,
    DEFAULT_COORTE_VALUE,
    DEFAULT_MES_INICIO,
    DEFAULT_ANO_INICIO,
    DEFAULT_MES_FIM,
    DEFAULT_ANO_FIM,
    DEFAULT_VARIAVEIS_CODIGOS,
    DEFAULT_TIPO_ESTIMATIVA_VALUE,
    DEFAULT_EXIBICAO_BOOL,
    DEFAULT_ORIENTACAO_VALUE,
    URL_WHITELIST,
    WATCHDOG_TIMEOUT_GLOBAL_S,
)
from infrastructure.browser.driver import create_driver, teardown_driver
from core.errors import NavigationError
from core.security import (
    sanitize_log_message,
    assert_url_whitelist,
    start_watchdog,
    check_watchdog,
)
from core.lock import SingleInstanceLock
from services.auth_service import AuthService
from services.navigation_service import NavigationService
from services.pesquisa_service import PesquisaService
from domain.models import PesquisaParams


def _fase0_carregar_settings():
    """FASE 0: Carrega settings + valida CNI_USER/CNI_PASSWORD (fail fast ANTES do browser)."""
    print("FASE 0: Carregando configurações de ambiente (.env)...", flush=True)
    cfg = get_settings()
    if not cfg.cni_user or not cfg.cni_password:
        raise RuntimeError(
            "CNI_USER e/ou CNI_PASSWORD ausentes em .env. "
            "Copie .env.example para .env e preencha credenciais válidas da federação CNI."
        )
    print(f"Settings OK: usuário='{cfg.cni_user[:2]}***'.", flush=True)
    return cfg


def _pipeline_completo() -> None:
    """Executa pipeline FASE1→FASE4 completo. Levanta exceção em qualquer falha não-recuperável.

    Integra SEG-2 (Whitelist), SEG-3 (Watchdog), SEG-4 (Sanitize) nos pontos críticos.
    """
    start_watchdog(WATCHDOG_TIMEOUT_GLOBAL_S)
    cfg = _fase0_carregar_settings()

    # ---------------------------------------------------------------
    # FASE 1: Criar driver Chrome (AC-2: NÃO há driver global)
    # ---------------------------------------------------------------
    print("\n FASE 1: Iniciando navegador Chrome (headless=False)...", flush=True)
    driver = create_driver(headless=False)
    print(f"Driver Chrome criado (session_id={(driver.session_id or '')[:8]}...).", flush=True)

    try:
        driver.get(URL_BASE_LOGIN)
        print(f"GET {URL_BASE_LOGIN} OK.", flush=True)
        assert_url_whitelist(driver, URL_WHITELIST)

        # -----------------------------------------------------------
        # FASE 1.2: Login (AuthService + @with_retry)
        # -----------------------------------------------------------
        check_watchdog("login")
        print("\n FASE 1.2: Autenticando na CNI...", flush=True)
        auth = AuthService(driver)
        login_ok, login_msg = auth.logar(cfg.cni_user, cfg.cni_password)
        if not login_ok:
            raise RuntimeError(
                f"FASE 1.2: Login FALHOU: {login_msg}. "
                "Verifique credenciais em .env (mensagem 'usuário não encontrado' = federação CNI recusou)."
            )
        print("Login bem-sucedido.", flush=True)
        assert_url_whitelist(driver, URL_WHITELIST)

        # -----------------------------------------------------------
        # FASE 2: Navegação menus → Por Atividade (NavigationService @with_retry)
        # -----------------------------------------------------------
        check_watchdog("navegacao")
        print("\n FASE 2: Navegando menus → Por Atividade...", flush=True)
        nav = NavigationService(driver)
        if not nav.navegar_para_form_parametros():
            raise NavigationError("FASE 2: navegar_para_form_parametros retornou False.")
        print("Chegou em tela de parâmetros (selectForm).", flush=True)
        assert_url_whitelist(driver, URL_WHITELIST)

        # -----------------------------------------------------------
        # FASE 3 + FASE 4: PesquisaService.pesquisar_exportar_excel @with_retry
        #   ORDEM RÍGIDA DENTRO do service (NÃO é decidida aqui no main):
        #   5 filtros → Estrato → Variáveis → Radios → Orientação → Pesquisar → Datatable → Export
        # -----------------------------------------------------------
        check_watchdog("pesquisa+export")
        print("\n FASE 3 + 4: Preenchendo parâmetros → Pesquisar → Exportar Excel...", flush=True)
        params = PesquisaParams(
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
        pesquisa_svc = PesquisaService(driver, params)
        if not pesquisa_svc.pesquisar_exportar_excel():
            raise RuntimeError("FASE 3+4: pesquisar_exportar_excel retornou False.")
        print("\n Excel iniciou download em background (pasta padrão Downloads do Chrome).", flush=True)
        assert_url_whitelist(driver, URL_WHITELIST)

    finally:
        # SEMPRE executa — independente de sucesso ou exceção
        print("\n Encerrando navegador (quit seguro)...", flush=True)
        try:
            teardown_driver(driver)
        except Exception:
            pass
        print("Navegador encerrado.", flush=True)


def main() -> None:
    """Entry point principal: pipeline + métrica tempo total + SEG-6 (single-instance lock)."""
    t0_global = time.time()
    lock_path = Path(__file__).resolve().parent / ".pipeline.lock"
    try:
        with SingleInstanceLock(lock_path):
            try:
                _pipeline_completo()
                total = time.time() - t0_global
                print(f"\n SUCESSO: pipeline completo finalizado em {total:.1f}s.", flush=True)
                time.sleep(3)
            except Exception as exc:
                total = time.time() - t0_global
                _msg = sanitize_log_message(str(exc))
                _repr = sanitize_log_message(repr(exc))
                print(f"\n FALHA após {total:.1f}s: {_msg}", flush=True)
                print(f"  [debug repr sanitizado] {_repr}", flush=True)
                raise
    except Exception as exc_lock:
        total = time.time() - t0_global
        _msg = sanitize_log_message(str(exc_lock))
        print(f"\n FALHA (pré-pipeline) após {total:.1f}s: {_msg}", flush=True)
        raise


if __name__ == "__main__":
    main()
