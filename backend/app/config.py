from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv, set_key


PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_DIR / "backend"
ROOT_DIR = PROJECT_DIR
NOTEBOOK_PATH = PROJECT_DIR / "notebooks" / "01_metadata_analysis.ipynb"
REPORTS_DIR = PROJECT_DIR / "reports"
DATA_DIR = PROJECT_DIR / "data"


ENV_PATH = PROJECT_DIR / ".env"


load_dotenv(ENV_PATH)
load_dotenv(BACKEND_DIR / ".env")


@dataclass
class Settings:
    app_host: str
    app_port: int
    contact_email: str
    database_path: Path
    ncbi_api_key: str
    openalex_api_key: str
    semantic_scholar_api_key: str
    core_api_key: str
    elsevier_api_key: str
    elsevier_inst_token: str
    web_of_science_api_key: str
    ieee_api_key: str


def build_settings() -> Settings:
    return Settings(
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        contact_email=os.getenv("CONTACT_EMAIL", ""),
        database_path=Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "metadata.sqlite"))),
        ncbi_api_key=os.getenv("NCBI_API_KEY", ""),
        openalex_api_key=os.getenv("OPENALEX_API_KEY", ""),
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY", ""),
        core_api_key=os.getenv("CORE_API_KEY", ""),
        elsevier_api_key=os.getenv("ELSEVIER_API_KEY", ""),
        elsevier_inst_token=os.getenv("ELSEVIER_INST_TOKEN", ""),
        web_of_science_api_key=os.getenv("WEB_OF_SCIENCE_API_KEY", ""),
        ieee_api_key=os.getenv("IEEE_API_KEY", ""),
    )


settings = build_settings()


ENV_FIELD_MAP = {
    "contact_email": "CONTACT_EMAIL",
    "ncbi_api_key": "NCBI_API_KEY",
    "openalex_api_key": "OPENALEX_API_KEY",
    "semantic_scholar_api_key": "SEMANTIC_SCHOLAR_API_KEY",
    "core_api_key": "CORE_API_KEY",
    "elsevier_api_key": "ELSEVIER_API_KEY",
    "elsevier_inst_token": "ELSEVIER_INST_TOKEN",
    "web_of_science_api_key": "WEB_OF_SCIENCE_API_KEY",
    "ieee_api_key": "IEEE_API_KEY",
}


KEY_METADATA = {
    "contact_email": {
        "label": "Contact email",
        "required_for": ["OpenAlex polite pool", "Crossref polite pool", "NCBI/PubMed tool email"],
        "help_text": "Recommended for polite API use and better reliability. This is not a secret.",
        "secret": False,
    },
    "ncbi_api_key": {
        "label": "NCBI API key",
        "required_for": ["PubMed / MEDLINE higher rate limits"],
        "help_text": "Optional. PubMed works without it, but an API key improves request limits.",
        "secret": True,
    },
    "openalex_api_key": {
        "label": "OpenAlex API key",
        "required_for": ["OpenAlex authenticated pool"],
        "help_text": "Optional for low-volume testing, recommended for reliable OpenAlex access and higher documented quotas.",
        "secret": True,
    },
    "semantic_scholar_api_key": {
        "label": "Semantic Scholar API key",
        "required_for": ["Optional Semantic Scholar higher rate limits"],
        "help_text": "Optional. Most Semantic Scholar metadata endpoints work without a key, but a key improves reliability for repeated or multi-string searches.",
        "secret": True,
    },
    "core_api_key": {
        "label": "CORE API key",
        "required_for": ["CORE"],
        "help_text": "Required to use the CORE connector.",
        "secret": True,
    },
    "elsevier_api_key": {
        "label": "Elsevier / Scopus API key",
        "required_for": ["Scopus"],
        "help_text": "Required for Scopus. Institutional entitlement may also be needed.",
        "secret": True,
    },
    "elsevier_inst_token": {
        "label": "Elsevier institution token",
        "required_for": ["Scopus institutional access"],
        "help_text": "Optional. Some Scopus access requires this token in addition to the API key.",
        "secret": True,
    },
    "web_of_science_api_key": {
        "label": "Web of Science API key",
        "required_for": ["Web of Science direct API"],
        "help_text": "Optional placeholder. Direct access depends on your Clarivate API entitlement.",
        "secret": True,
    },
    "ieee_api_key": {
        "label": "IEEE Xplore API key",
        "required_for": ["IEEE Xplore"],
        "help_text": "Required for IEEE Xplore metadata search through the IEEE API.",
        "secret": True,
    },
}


def mask_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"


def settings_status() -> list[dict[str, object]]:
    values = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    status: list[dict[str, object]] = []
    for field_name, env_name in ENV_FIELD_MAP.items():
        value = os.getenv(env_name, values.get(env_name, "") or "")
        meta = KEY_METADATA[field_name]
        status.append(
            {
                "field": field_name,
                "env_name": env_name,
                "label": meta["label"],
                "required_for": meta["required_for"],
                "help_text": meta["help_text"],
                "secret": meta["secret"],
                "configured": bool(value),
                "masked_value": mask_value(value),
            }
        )
    return status


def update_env_settings(updates: dict[str, str]) -> None:
    ENV_PATH.touch(exist_ok=True)
    for field_name, value in updates.items():
        if field_name not in ENV_FIELD_MAP:
            continue
        env_name = ENV_FIELD_MAP[field_name]
        clean_value = value.strip()
        set_key(str(ENV_PATH), env_name, clean_value)
        os.environ[env_name] = clean_value
    refreshed = build_settings()
    settings.__dict__.update(refreshed.__dict__)
