from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_graph: str = "darkmatter"
    demo_base_url: str = "http://localhost:8001"
    dry_run: bool = True
    alert_allowlist: str = "oncall@example.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = "darkmatter@example.com"
    gemini_api_key: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowlist(self) -> set[str]:
        return {item.strip().lower() for item in self.alert_allowlist.split(",") if item.strip()}


settings = Settings()
