"""
SingleInstanceLock (SEG-6): Garante que SOMENTE UMA instância do pipeline está rodando.

Implementação cross-platform com fallback:
  - Windows: msvcrt.locking() + arquivo de PID
  - Linux/macOS: fcntl.flock() + arquivo de PID
  - Fallback geral: cria arquivo de PID, verifica se PID ainda está vivo

Uso RECOMENDADO como context manager (garante liberação no finally):

    with SingleInstanceLock(Path(".pipeline.lock")):
        rodar_pipeline()
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from core.errors import AppError


class SingleInstanceLockError(AppError):
    """Levantado quando já existe OUTRA instância do pipeline rodando."""
    pass


class SingleInstanceLock:
    """
    Lock de nível de processo baseado em arquivo, cross-platform.

    Args:
        path: caminho do arquivo de lock (ex: ".pipeline.lock")
        stale_check: se True, verifica se o PID escrito no lock ainda está vivo.
        stale_timeout_s: tolerância para considerar lock "órfão" de crash anterior.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        stale_check: bool = True,
        stale_timeout_s: int = 30,
    ):
        self._path = Path(path)
        self._stale_check = bool(stale_check)
        self._stale_timeout_s = int(stale_timeout_s)
        self._fh: Optional[object] = None
        self._locked = False

    # ------------------------------------------------------------------
    # Implementação cross-platform: _adquirir_plataforma / _liberar_plataforma
    # ------------------------------------------------------------------
    def _pid_atual(self) -> int:
        return os.getpid()

    @staticmethod
    def _pid_esta_vivo(pid: int) -> bool:
        """Cross-platform: verifica se um dado PID ainda tem processo vivo."""
        if pid <= 0:
            return False
        if sys.platform.startswith("win"):
            try:
                import ctypes
                PROCESS_QUERY_INFORMATION = 0x0400
                SYNCHRONIZE = 0x00100000
                k32 = ctypes.WinDLL("kernel32", use_last_error=True)
                OpenProcess = k32.OpenProcess
                OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
                OpenProcess.restype = ctypes.c_void_p
                CloseHandle = k32.CloseHandle
                CloseHandle.argtypes = [ctypes.c_void_p]
                CloseHandle.restype = ctypes.c_int
                handle = OpenProcess(PROCESS_QUERY_INFORMATION | SYNCHRONIZE, 0, pid)
                if not handle:
                    return False
                try:
                    return True
                finally:
                    CloseHandle(handle)
            except Exception:
                try:
                    os.kill(pid, 0)
                    return True
                except (ProcessLookupError, PermissionError, OSError):
                    return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except (ProcessLookupError, PermissionError, OSError):
                return False

    def _ler_lock_pid_e_mtime(self) -> tuple[Optional[int], Optional[float]]:
        try:
            texto = self._path.read_text(encoding="utf-8").strip()
            if not texto:
                return None, None
            linhas = [ln for ln in texto.splitlines() if ln.strip()]
            pid_s = linhas[0].split("|", 1)[0].strip()
            try:
                pid = int(pid_s)
            except ValueError:
                pid = None
            try:
                mtime = self._path.stat().st_mtime
            except OSError:
                mtime = None
            return pid, mtime
        except OSError:
            return None, None

    def _escrever_lock_pid(self) -> None:
        conteudo = f"{self._pid_atual()}|{time.time():.3f}\n"
        if self._fh is None:
            self._path.write_text(conteudo, encoding="utf-8")
            return
        try:
            self._fh.seek(0)  # type: ignore[attr-defined]
            self._fh.truncate()  # type: ignore[attr-defined]
            self._fh.write(conteudo)  # type: ignore[attr-defined]
            try:
                self._fh.flush()  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            self._path.write_text(conteudo, encoding="utf-8")

    def _stale_check_or_remove(self) -> None:
        """Se lock existe mas o processo está morto OU mtime muito antigo, remove."""
        if not self._stale_check:
            return
        if not self._path.exists():
            return
        pid, mtime = self._ler_lock_pid_e_mtime()
        agora = time.time()
        mtime = mtime or agora
        idade = max(0.0, agora - mtime)
        parece_orfao = False
        if pid is not None and pid > 0 and pid != self._pid_atual():
            if not self._pid_esta_vivo(pid):
                parece_orfao = True
        if idade > max(self._stale_timeout_s, 300):
            parece_orfao = True
        if parece_orfao:
            try:
                self._path.unlink(missing_ok=True)
            except OSError:
                pass

    def _try_lock_windows(self, timeout_total_s: float = 2.0) -> bool:
        try:
            import msvcrt
        except ImportError:
            return False
        self._stale_check_or_remove()
        try:
            fh = open(self._path, "a+b")
        except OSError:
            return False
        t0 = time.monotonic()
        while True:
            try:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    self._fh = fh
                    return True
                except OSError:
                    pass
                if (time.monotonic() - t0) >= timeout_total_s:
                    try:
                        fh.close()
                    except Exception:
                        pass
                    return False
                time.sleep(0.08)
            except Exception:
                try:
                    fh.close()
                except Exception:
                    pass
                return False

    def _try_lock_posix(self, timeout_total_s: float = 2.0) -> bool:
        try:
            import fcntl
        except ImportError:
            return False
        self._stale_check_or_remove()
        try:
            fh = open(self._path, "a+b")
        except OSError:
            return False
        t0 = time.monotonic()
        while True:
            try:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._fh = fh
                    return True
                except BlockingIOError:
                    pass
                if (time.monotonic() - t0) >= timeout_total_s:
                    try:
                        fh.close()
                    except Exception:
                        pass
                    return False
                time.sleep(0.08)
            except Exception:
                try:
                    fh.close()
                except Exception:
                    pass
                return False

    def _try_lock_fallback(self) -> bool:
        """Fallback: cria arquivo com O_EXCL ou testa PID/vivo."""
        self._stale_check_or_remove()
        try:
            fd = os.open(str(self._path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.close(fd)
            self._escrever_lock_pid()
            return True
        except FileExistsError:
            pid, _mtime = self._ler_lock_pid_e_mtime()
            if pid is None or not self._pid_esta_vivo(pid):
                try:
                    self._path.unlink(missing_ok=True)
                except OSError:
                    pass
                try:
                    fd = os.open(str(self._path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                    os.close(fd)
                    self._escrever_lock_pid()
                    return True
                except FileExistsError:
                    return False
            return False
        except OSError:
            return False

    def _unlock_plataforma(self) -> None:
        if self._fh is not None:
            try:
                if sys.platform.startswith("win"):
                    try:
                        import msvcrt
                        msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                else:
                    try:
                        import fcntl
                        fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self._fh.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._fh = None
        try:
            if self._path.exists():
                conteudo = self._path.read_text(encoding="utf-8").strip()
                if conteudo.startswith(f"{self._pid_atual()}|") or not conteudo:
                    self._path.unlink(missing_ok=True)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # API público context manager
    # ------------------------------------------------------------------
    def acquire(self) -> None:
        """Adquire o lock. Levanta SingleInstanceLockError se já houver outra instância."""
        if self._locked:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        ok = False
        outro_pid: Optional[int] = None
        if sys.platform.startswith("win"):
            ok = self._try_lock_windows(timeout_total_s=1.5)
        else:
            ok = self._try_lock_posix(timeout_total_s=1.5)
        if not ok:
            ok = self._try_lock_fallback()
        if not ok:
            outro_pid, _m = self._ler_lock_pid_e_mtime()
            detalhe = f" (PID ativo no lock: {outro_pid})" if outro_pid else ""
            raise SingleInstanceLockError(
                "Outra instância do pipeline já está em execução"
                f"{detalhe}. Encerre a outra antes de iniciar, ou remova o arquivo "
                f"lock caso seja um crash anterior: '{self._path}'."
            )
        try:
            self._escrever_lock_pid()
        except Exception:
            pass
        self._locked = True

    def release(self) -> None:
        """Libera o lock (idempotente)."""
        if not self._locked:
            return
        self._unlock_plataforma()
        self._locked = False

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


__all__ = ["SingleInstanceLock", "SingleInstanceLockError"]
