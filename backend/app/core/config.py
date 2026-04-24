from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_LLM_SYSTEM_PROMPT_FILE = "backend/prompts/stock-assistant-system-prompt.txt"
DEFAULT_LLM_SHORT_TERM_PROMPT_FILE = "backend/prompts/stock-assistant-short-term-prompt.txt"
DEFAULT_LLM_SWING_PROMPT_FILE = "backend/prompts/stock-assistant-swing-prompt.txt"
DEFAULT_LLM_MID_TERM_VALUE_PROMPT_FILE = (
    "backend/prompts/stock-assistant-mid-term-value-prompt.txt"
)


def _strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, _strip_env_value(value))


def _load_root_env_file() -> None:
    _load_dotenv_file(ROOT_ENV_FILE)


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            return value
    return default


def _env_bool(*names: str, default: bool = False) -> bool:
    raw = _env(*names, default="true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


_load_root_env_file()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Wencai Skills Assistant"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    backend_root: Path = BACKEND_ROOT
    project_root: Path = PROJECT_ROOT
    data_dir: Path = BACKEND_ROOT / "data"
    iwencai_base_url: str = os.environ.get(
        "IWENCAI_BASE_URL", "https://openapi.iwencai.com"
    ).rstrip("/")
    iwencai_api_key: str = os.environ.get("IWENCAI_API_KEY", "")
    openai_auth_mode: str = _env("OPENAI_AUTH_MODE", default="apikey")
    openai_base_url: str = _env(
        "OPENAI_BASE_URL",
        "openai_base_url",
        default="https://api.openai.com/v1",
    ).rstrip("/")
    openai_api_key: str = _env("OPENAI_API_KEY")
    openai_model: str = _env("OPENAI_MODEL", "model", default="gpt-5.4")
    openai_model_reasoning_effort: str = _env(
        "OPENAI_MODEL_REASONING_EFFORT",
        "MODEL_REASONING_EFFORT",
        "model_reasoning_effort",
        default="medium",
    )
    openai_timeout_seconds: int = int(_env("OPENAI_TIMEOUT_SECONDS", default="90"))
    llm_chain_mode: str = _env("LLM_CHAIN_MODE", default="auto")
    llm_account_pool_adapter: str = _env("LLM_ACCOUNT_POOL_ADAPTER", default="env")
    llm_system_prompt: str = _env("LLM_SYSTEM_PROMPT")
    llm_system_prompt_file: str = _env(
        "LLM_SYSTEM_PROMPT_FILE",
        default=DEFAULT_LLM_SYSTEM_PROMPT_FILE,
    )
    llm_short_term_prompt: str = _env("LLM_SHORT_TERM_PROMPT")
    llm_short_term_prompt_file: str = _env(
        "LLM_SHORT_TERM_PROMPT_FILE",
        default=DEFAULT_LLM_SHORT_TERM_PROMPT_FILE,
    )
    llm_swing_prompt: str = _env("LLM_SWING_PROMPT")
    llm_swing_prompt_file: str = _env(
        "LLM_SWING_PROMPT_FILE",
        default=DEFAULT_LLM_SWING_PROMPT_FILE,
    )
    llm_mid_term_value_prompt: str = _env("LLM_MID_TERM_VALUE_PROMPT")
    llm_mid_term_value_prompt_file: str = _env(
        "LLM_MID_TERM_VALUE_PROMPT_FILE",
        default=DEFAULT_LLM_MID_TERM_VALUE_PROMPT_FILE,
    )
    sim_trading_accounts_dir: str = _env("SIM_TRADING_ACCOUNTS_DIR")
    sim_trading_auto_open: bool = _env_bool("SIM_TRADING_AUTO_OPEN", default=True)
    sim_trading_department_id: str = _env("SIM_TRADING_DEPARTMENT_ID", default="997376")
    sim_trading_timeout_seconds: int = int(_env("SIM_TRADING_TIMEOUT_SECONDS", default="15"))
    openai_account_pool_json: str = _env("OPENAI_ACCOUNT_POOL_JSON")
    anthropic_base_url: str = _env(
        "ANTHROPIC_BASE_URL",
        default="",
    ).rstrip("/")
    anthropic_auth_token: str = _env("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY")
    anthropic_model: str = _env("ANTHROPIC_MODEL", default="MiniMax-M2.7")
    anthropic_timeout_seconds: int = int(_env("ANTHROPIC_TIMEOUT_SECONDS", default="90"))
    anthropic_account_pool_json: str = _env(
        "ANTHROPIC_ACCOUNT_POOL_JSON",
        "MINIMAX_ACCOUNT_POOL_JSON",
    )
    watch_monitor_enabled: bool = _env_bool("WATCH_MONITOR_ENABLED", default=True)
    watch_monitor_interval_seconds: int = int(_env("WATCH_MONITOR_INTERVAL_SECONDS", default="60"))
    watch_monitor_event_cooldown_seconds: int = int(
        _env("WATCH_MONITOR_EVENT_COOLDOWN_SECONDS", default="900")
    )
    watch_monitor_max_events: int = int(_env("WATCH_MONITOR_MAX_EVENTS", default="200"))
    watch_notification_timeout_seconds: int = int(
        _env("WATCH_NOTIFICATION_TIMEOUT_SECONDS", default="10")
    )
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    @property
    def skills_root(self) -> Path:
        return self.project_root / "skills"

    @property
    def sim_trading_skill_root(self) -> Path:
        return self.skills_root / "模拟炒股"

    @property
    def effective_sim_trading_accounts_dir(self) -> Path:
        configured = self.sim_trading_accounts_dir.strip()
        if configured:
            resolved = self.resolve_optional_path(configured)
            if resolved is not None:
                return resolved

        legacy_dir = Path("/workspace/projects/workspace/user_accounts")
        if legacy_dir.exists():
            return legacy_dir

        return self.data_dir / "user_accounts"

    @property
    def sim_trading_enabled(self) -> bool:
        return (
            self.sim_trading_skill_root.exists()
            and (self.sim_trading_skill_root / "scripts" / "stock_query.py").exists()
        )

    def resolve_optional_path(self, raw_path: str) -> Path | None:
        text = raw_path.strip()
        if not text:
            return None

        path = Path(text)
        if path.is_absolute():
            return path

        project_candidate = (self.project_root / path).resolve()
        backend_candidate = (self.backend_root / path).resolve()
        if project_candidate.exists() or not backend_candidate.exists():
            return project_candidate
        return backend_candidate

    def _resolve_prompt_text(self, inline_prompt: str, raw_path: str, *, label: str) -> str:
        text = inline_prompt.strip()
        if text:
            return text

        prompt_path = self.resolve_optional_path(raw_path)
        if prompt_path is None:
            raise ValueError(f"{label} 或对应的 FILE 至少要配置一个")
        if not prompt_path.exists():
            raise FileNotFoundError(f"{label}_FILE 不存在: {prompt_path}")

        prompt_text = prompt_path.read_text(encoding="utf-8").strip()
        if not prompt_text:
            raise ValueError(f"{label}_FILE 为空: {prompt_path}")
        return prompt_text

    @property
    def effective_llm_system_prompt(self) -> str:
        return self._resolve_prompt_text(
            self.llm_system_prompt,
            self.llm_system_prompt_file,
            label="LLM_SYSTEM_PROMPT",
        )

    @property
    def llm_system_prompt_source(self) -> str:
        if self.llm_system_prompt.strip():
            return "env"
        return "file"

    def effective_llm_mode_prompt(self, mode_key: str) -> str:
        if mode_key == "short_term":
            return self._resolve_prompt_text(
                self.llm_short_term_prompt,
                self.llm_short_term_prompt_file,
                label="LLM_SHORT_TERM_PROMPT",
            )
        if mode_key == "swing":
            return self._resolve_prompt_text(
                self.llm_swing_prompt,
                self.llm_swing_prompt_file,
                label="LLM_SWING_PROMPT",
            )
        if mode_key == "mid_term_value":
            return self._resolve_prompt_text(
                self.llm_mid_term_value_prompt,
                self.llm_mid_term_value_prompt_file,
                label="LLM_MID_TERM_VALUE_PROMPT",
            )
        return ""

    @property
    def llm_system_prompt_role(self) -> str:
        for raw_line in self.effective_llm_system_prompt.splitlines():
            line = raw_line.strip()
            if line:
                return line[:120]
        raise ValueError("LLM system prompt 不能为空")

    @property
    def openai_enabled(self) -> bool:
        return bool(
            self.openai_account_pool_json.strip()
            or (self.openai_api_key.strip() and self.openai_model.strip())
        )

    @property
    def anthropic_enabled(self) -> bool:
        return bool(
            self.anthropic_account_pool_json.strip()
            or (
                self.anthropic_base_url.strip()
                and self.anthropic_auth_token.strip()
                and self.anthropic_model.strip()
            )
        )

    @property
    def llm_enabled(self) -> bool:
        return self.openai_enabled or self.anthropic_enabled


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.effective_llm_system_prompt
    settings.effective_llm_mode_prompt("short_term")
    settings.effective_llm_mode_prompt("swing")
    settings.effective_llm_mode_prompt("mid_term_value")
    return settings
