"""
Carregamento de configurações de ambiente e credenciais via variáveis de ambiente.

Usa python-dotenv para carregar .env e pydantic-settings BaseSettings.
Q1 aprovado SIM → usa Pydantic (preferência Zod/Pydantic do perfil).

Integração de SEGURANÇA (SEG-4 / SEG-5):
  - check_env_file_permissions ao carregar .env
  - sanitize_log_message em mensagens de erro de credenciais
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE: bool = True
except ImportError:  # pragma: no cover - defensive import error
    _DOTENV_AVAILABLE = False

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _PYDANTIC_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _PYDANTIC_AVAILABLE = False

from core.errors import ValidationError
from core.security import check_env_file_permissions, sanitize_log_message


# -------------------------------------------------------------------
# Classes concretas (uma para Settings — primeira Pydantic, fallback dataclass built-in
# se houver problema de import. Validação SEMPRE executada.
# -------------------------------------------------------------------
if _PYDANTIC_AVAILABLE:

    class Settings(BaseSettings):
        """Configurações de execução carregadas de env/.env (Pydantic BaseSettings)."""
        model_config = SettingsConfigDict(
            env_file=str(Path(__file__).resolve().parent.parent / ".env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

        cni_user: str = Field(..., description="Usuário CNI (e-mail institucional")
        cni_password: str = Field(..., description="Senha CNI (obtida junto à federação")

        @classmethod
        def model_validate_env(cls) -> "Settings":
            """Sobrescrevemos para ValidationError do core.errors em vez de PydanticValidationError."""
            try:
                inst = cls()
            except Exception as e:
                faltam: list[str] = []
                if not os.getenv("CNI_USER"):
                    faltam.append("CNI_USER")
                if not os.getenv("CNI_PASSWORD"):
                    faltam.append("CNI_PASSWORD")
                msg = "Variáveis de ambiente ausentes ou inválidas: " + ", ".join(faltam) if faltam else str(e)
                raise ValidationError(sanitize_log_message(msg)) from e
            # Validação extra: nenhum dos dois pode ser vazio
            if (not inst.cni_user.strip()) or (not inst.cni_password.strip()):
                faltam2: list[str] = []
                if not inst.cni_user.strip():
                    faltam2.append("CNI_USER")
                if not inst.cni_password.strip():
                    faltam2.append("CNI_PASSWORD")
                raise ValidationError(
                    sanitize_log_message(
                        "As seguintes variáveis de ambiente estão VAZIAS: "
                        + ", ".join(faltam2)
                        + ". Salve como .env no diretório raiz do projeto (veja .env.example)."
                    )
                )
            return inst

else:  # Dataclass de fallback integrada

    from dataclasses import dataclass

    @dataclass
    class Settings:  # type: ignore[no-redef]
        cni_user: str
        cni_password: str


# -------------------------------------------------------------------
# Carregador singleton do .env
# -------------------------------------------------------------------
_CARREGADO_DOTENV: bool = False


def _carregar_dotenv_se_ainda_nao() -> None:
    """Carrega .env uma única vez usando python-dotenv se disponível."""
    global _CARREGADO_DOTENV
    if _CARREGADO_DOTENV:
        return
    if _DOTENV_AVAILABLE:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False, verbose=False)
            # SEG-5: Verificar permissões do arquivo .env
            ok_perm, msg_warn = check_env_file_permissions(env_path)
            if not ok_perm and msg_warn:
                print(msg_warn, flush=True)
    _CARREGADO_DOTENV = True


def get_settings() -> Settings:
    """Retorna Settings carregada e validada. Levanta ValidationError em caso de ausência de credenciais."""
    _carregar_dotenv_se_ainda_nao()

    if _PYDANTIC_AVAILABLE:
        # validação pelo model_validate_env():
        return Settings.model_validate_env()  # type: ignore[attr-defined]

    # Fallback dataclass manual validation __post_init__ style:
    usr = os.getenv("CNI_USER", "").strip()
    pwd = os.getenv("CNI_PASSWORD", "").strip()
    faltam: list[str] = []
    if not usr:
        faltam.append("CNI_USER")
    if not pwd:
        faltam.append("CNI_PASSWORD")
    if faltam:
        raise ValidationError(
            sanitize_log_message(
                "As seguintes variáveis de ambiente estão AUSENTES: "
                + ", ".join(faltam)
                + ". Crie um arquivo .env no diretório raiz (copie .env.example e preencha com valores válidos fornecidos pela federação."
            )
        )
    return Settings(cni_user=usr, cni_password=pwd)


__all__ = ["Settings", "get_settings"]
