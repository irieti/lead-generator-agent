from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field


class MeConfig(BaseModel):
    name: str
    role: str
    offer: str
    calendar_link: str = ""


class ICPConfig(BaseModel):
    description: str
    roles: list[str] = []
    industries: list[str] = []
    company_size: str = ""
    locations: list[str] = []
    pain_points: list[str] = []
    disqualifiers: list[str] = []


class ToneConfig(BaseModel):
    style: str
    avoid: list[str] = []
    message_length: str = "3-4 sentences"
    cta: str = "suggest a short call"


class ProspectingConfig(BaseModel):
    leads_per_run: int = 5
    research_depth: str = "medium"
    check_existing_crm: bool = True
    auto_send_if_hot: bool = False


class InboxConfig(BaseModel):
    check_last_hours: int = 2
    auto_reply_if_existing_client: bool = False
    classify_and_skip_spam: bool = True


class ScheduleConfig(BaseModel):
    prospect_time: str = "09:00"
    inbox_interval_hours: int = 2


class CRMConfig(BaseModel):
    worksheet: str = "Leads"
    extra_columns: list[str] = []


class ContentFormatConfig(BaseModel):
    length: str = "short — 3 to 5 short paragraphs"
    style: str = "conversational, one strong opening line"
    cta: str = "end with a question or provocative statement"


class ContentScheduleConfig(BaseModel):
    enabled: bool = True
    times: list[str] = ["08:30"]
    days: list[str] = ["mon", "wed", "fri"]


class ContentConfig(BaseModel):
    voice: str = "direct and opinionated practitioner"
    topics: list[str] = []
    format: ContentFormatConfig = Field(default_factory=ContentFormatConfig)
    examples: list[str] = []
    schedule: ContentScheduleConfig = Field(default_factory=ContentScheduleConfig)


class AgentConfig(BaseModel):
    me: MeConfig
    icp: ICPConfig
    tone: ToneConfig
    prospecting: ProspectingConfig = Field(default_factory=ProspectingConfig)
    inbox: InboxConfig = Field(default_factory=InboxConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    crm: CRMConfig = Field(default_factory=CRMConfig)
    content: ContentConfig = Field(default_factory=ContentConfig)


_config: Optional[AgentConfig] = None


def load_agent_config(path: str = "agent.config.yaml") -> AgentConfig:
    global _config
    if _config is not None:
        return _config
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"agent.config.yaml not found at {config_path.absolute()}. "
            "Copy agent.config.yaml.example and fill in your details."
        )
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    _config = AgentConfig(**raw)
    return _config


def get_config() -> AgentConfig:
    return load_agent_config()
