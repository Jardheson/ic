"""
Ajudantes de Segurança da Aplicação

Implementa:
  - sanitize_log_message (evita vazamento de credenciais em logs/tracebacks)
  - assert_url_whitelist (garante que só navega em domínios autorizados)
  - check_env_file_permissions (alerta se .env estiver em modo world-readable)
  - Watchdog global (timeout total do pipeline contra loop infinito)

Tudo usa stdlib; nenhuma dependência nova.
"""
from __future__ import annotations

import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Iterable, Optional, Tuple

from core.errors import AppError, TimeoutError as AppTimeoutError


# -------------------------------------------------------------------
# SEG-4 / SEG-1: Sanitização de mensagens de log
# -------------------------------------------------------------------
SECURE_LOG_KEYWORDS: tuple[str, ...] = (
    "PASSWORD", "PASSWD", "SENHA",
    "SECRET", "TOKEN", "API_KEY", "CHAVE",
    "CNI_PASSWORD", "CNI_USER",
)

_SENSITIVE_VALUE_MASK: str = "***"


def sanitize_log_message(msg: object) -> str:
    """
    Remove/substitui valores sensíveis de mensagens que serão logadas.

    Estratégia:
      1. Converte para str.
      2. Para cada keyword sensível, encontra KEYWORD=valor (ou KEYWORD: valor,
         ou KEYWORD "valor") e substitui o valor por ***.
      3. Também cobre "password=xyz", "senha : xyz", etc.
    """
    if msg is None:
        return ""
    s = str(msg)
    if not s:
        return s
    flags = re.IGNORECASE
    patterns = [
        rf"\b({ '|'.join(map(re.escape, SECURE_LOG_KEYWORDS)) })\b\s*[=:]\s*[\"']?([^\s,;\"'&)]+)[\"']?",
        rf"[\"']({ '|'.join(map(re.escape, SECURE_LOG_KEYWORDS)) })[\"']\s*[=:]\s*[\"']?([^\s,;\"'&)]+)[\"']?",
    ]
    for pat in patterns:
        def _sub(m: re.Match) -> str:
            kw = m.group(1)
            sep = m.group(0)[len(kw):]
            idx_eq = -1
            for ch in ("=", ":"):
                i = sep.find(ch)
                if i >= 0 and (idx_eq < 0 or i < idx_eq):
                    idx_eq = i
            if idx_eq < 0:
                return f"{kw}={_SENSITIVE_VALUE_MASK}"
            sep_prefix = sep[: idx_eq + 1]
            return f"{kw}{sep_prefix}{_SENSITIVE_VALUE_MASK}"
        s = re.sub(pat, _sub, s, flags=flags)
    return s


# -------------------------------------------------------------------
# SEG-2: Validação de URL Whitelist
# -------------------------------------------------------------------
class URLWhitelistError(AppError):
    """URL atual do navegador NÃO está na whitelist de domínios permitidos."""
    pass


def assert_url_whitelist(driver, allowed_hosts: Iterable[str]) -> None:
    """
    Valida que o hostname da URL atual do driver pertence a allowed_hosts.

    Aceita:
      - driver: webdriver.Chrome (qualquer coisa com .current_url ou execute_script)
      - allowed_hosts: set/list de hostnames (ex: {"pesquisasconjunturais.cni.com.br"})

    Raises:
      URLWhitelistError: se a navegação estiver em domínio não autorizado.
    """
    allowed = {h.strip().lower() for h in allowed_hosts if h and str(h).strip()}
    if not allowed:
        return
    hostname = ""
    try:
        url = str(getattr(driver, "current_url", "") or "").strip()
        if not url and hasattr(driver, "execute_script"):
            try:
                url = str(driver.execute_script("return (document.location && document.location.href) || '';") or "").strip()
            except Exception:
                url = ""
        if url:
            from urllib.parse import urlparse
            hostname = (urlparse(url).hostname or "").lower().strip()
    except Exception:
        hostname = ""
    if not hostname:
        raise URLWhitelistError(
            "Não foi possível obter o hostname da URL atual. "
            "Whitelist não pode ser validada (bloqueando por segurança)."
        )
    if hostname not in allowed:
        def _eh_subdominio(h: str, base: str) -> bool:
            b = base.lower().lstrip(".")
            return h == b or h.endswith("." + b)
        if not any(_eh_subdominio(hostname, b) for b in allowed):
            raise URLWhitelistError(
                f"URL host='{hostname}' NÃO está na whitelist de domínios permitidos "
                f"(allowed={sorted(allowed)}). Bloqueando execução por segurança."
            )


# -------------------------------------------------------------------
# SEG-5: Permissões de arquivo .env
# -------------------------------------------------------------------
def check_env_file_permissions(env_path: Path) -> Tuple[bool, str]:
    """
    Verifica se o arquivo .env tem permissões seguras.

    Regras:
      - Linux/macOS: somente owner pode ler/escrever (modo & 0o077 == 0 → modo 0o600).
      - Windows: tenta verificar ACLs; se não for possível, retorna (True, "") sem warning.

    Returns:
      (ok_bool, mensagem_warning_ou_vazia)
    """
    p = Path(env_path)
    if not p.exists() or not p.is_file():
        return True, ""
    try:
        if sys.platform.startswith("win"):
            try:
                import ctypes
                from ctypes import wintypes
                advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
                EVERYONE_SID = "S-1-1-0"
                def _convert_sid(sid_str):
                    psid = ctypes.c_void_p()
                    if not advapi32.ConvertStringSidToSidW(sid_str, ctypes.byref(psid)):
                        return None
                    return psid
                everyone = _convert_sid(EVERYONE_SID)
                if everyone is None:
                    return True, ""
                return True, ""
            except Exception:
                return True, ""
        modo = stat.S_IMODE(p.stat().st_mode)
        outros_acessam = modo & 0o077
        if outros_acessam != 0:
            warning = (
                f"⚠️  Arquivo .env com permissões inseguras (modo=0o{modo:o}). "
                "Grupo/outros podem ler credenciais. Ajuste com: chmod 600 .env"
            )
            return False, warning
        return True, ""
    except Exception:
        return True, ""


# -------------------------------------------------------------------
# SEG-3: Watchdog Global (timeout total do pipeline)
# -------------------------------------------------------------------
_WATCHDOG_STARTED_AT: Optional[float] = None
_WATCHDOG_TIMEOUT_S: Optional[float] = None
_WATCHDOG_WARNED_AT: Optional[float] = None


def start_watchdog(timeout_s: int | float) -> None:
    """Inicia o cronômetro do watchdog. timeout_s = duração máxima total permitida."""
    global _WATCHDOG_STARTED_AT, _WATCHDOG_TIMEOUT_S, _WATCHDOG_WARNED_AT
    if timeout_s <= 0:
        raise ValueError(f"timeout_s precisa ser > 0 (recebeu {timeout_s})")
    _WATCHDOG_STARTED_AT = time.monotonic()
    _WATCHDOG_TIMEOUT_S = float(timeout_s)
    _WATCHDOG_WARNED_AT = None


def watchdog_remaining_s() -> Optional[float]:
    """Retorna segundos restantes (float), ou None se o watchdog não foi iniciado."""
    if _WATCHDOG_STARTED_AT is None or _WATCHDOG_TIMEOUT_S is None:
        return None
    decorrido = time.monotonic() - _WATCHDOG_STARTED_AT
    return max(0.0, _WATCHDOG_TIMEOUT_S - decorrido)


def check_watchdog(operation_label: str) -> None:
    """
    Verifica se o tempo total do pipeline já passou do limite.
    - Se faltar <= 300s (5 min) → emite WARNING 1 vez por hora.
    - Se tiver passado do limite → levanta core.errors.TimeoutError (AppTimeoutError).
    """
    remaining = watchdog_remaining_s()
    if remaining is None:
        return
    global _WATCHDOG_WARNED_AT
    decorrido = time.monotonic() - _WATCHDOG_STARTED_AT
    if remaining <= 0.0:
        raise AppTimeoutError(
            f"WATCHDOG GLOBAL: tempo máximo ultrapassado antes de '{operation_label}' "
            f"(decorrido={decorrido:.0f}s, limite={_WATCHDOG_TIMEOUT_S:.0f}s). "
            "Abortando para evitar loop infinito."
        )
    if remaining <= 300.0:
        agora = time.monotonic()
        if _WATCHDOG_WARNED_AT is None or (agora - _WATCHDOG_WARNED_AT) >= 60.0:
            _WATCHDOG_WARNED_AT = agora
            print(
                f"  ⚠️  WATCHDOG: restam apenas {remaining:.0f}s antes de '{operation_label}' "
                f"(total limite={_WATCHDOG_TIMEOUT_S:.0f}s).",
                flush=True,
            )


__all__ = [
    "SECURE_LOG_KEYWORDS",
    "sanitize_log_message",
    "URLWhitelistError",
    "assert_url_whitelist",
    "check_env_file_permissions",
    "start_watchdog",
    "check_watchdog",
    "watchdog_remaining_s",
]
