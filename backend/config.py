from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    openai_api_key: str
    tavily_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./data/agent.db"
    http_tool_allowed_domains: str = ""
    max_agent_iterations: int = 15
    tool_max_retries: int = 2

    @property
    def http_allowed_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.http_tool_allowed_domains.split(",") if d.strip()]


settings = Settings()
