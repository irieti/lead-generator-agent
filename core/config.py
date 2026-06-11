from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-opus-4-5", alias="ANTHROPIC_MODEL")

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(..., alias="TELEGRAM_CHAT_ID")
    telegram_approval_timeout: int = Field(300, alias="TELEGRAM_APPROVAL_TIMEOUT")

    # Gmail
    gmail_credentials_json: str = Field("./gmail_credentials.json", alias="GMAIL_CREDENTIALS_JSON")
    gmail_token_json: str = Field("./gmail_token.json", alias="GMAIL_TOKEN_JSON")

    # Google Sheets
    google_sheet_id: str = Field(..., alias="GOOGLE_SHEET_ID")
    google_service_account_json: str = Field("./service_account.json", alias="GOOGLE_SERVICE_ACCOUNT_JSON")

    # LinkedIn (browser automation — prospecting)
    linkedin_email: str = Field(..., alias="LINKEDIN_EMAIL")
    linkedin_password: str = Field(..., alias="LINKEDIN_PASSWORD")
    linkedin_headless: bool = Field(True, alias="LINKEDIN_HEADLESS")
    linkedin_daily_invite_limit: int = Field(10, alias="LINKEDIN_DAILY_INVITE_LIMIT")
    linkedin_delay_between_actions: int = Field(3, alias="LINKEDIN_DELAY_BETWEEN_ACTIONS")

    # LinkedIn API (posting via official API)
    linkedin_client_id: str = Field("", alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str = Field("", alias="LINKEDIN_CLIENT_SECRET")
    linkedin_redirect_uri: str = Field("http://localhost:3000/callback", alias="LINKEDIN_REDIRECT_URI")
    linkedin_access_token: str = Field("", alias="LINKEDIN_ACCESS_TOKEN")

    # App
    app_host: str = Field("0.0.0.0", alias="APP_HOST")
    app_port: int = Field(8000, alias="APP_PORT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")


settings = Settings()
