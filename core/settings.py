from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class config(BaseSettings):
    AOAI_API_KEY: str
    AOAI_ENDPOINT: str
    AOAI_API_VERSION: str
    # AOAI_DEPLOY_GPT4O: str
    # AOAI_EMBEDDING_DEPLOYMENT: str

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    def get_llm(self):
        return AzureChatOpenAI(
            openai_api_key=self.AOAI_API_KEY,
            azure_endpoint=self.AOAI_ENDPOINT,
            api_version=self.AOAI_API_VERSION,
            # azure_deployment=self.AOAI_DEPLOY_GPT4O,
            azure_deployment="gpt-4o",
            temperature=0.7,
            streaming=True,
        )

    def get_embeddings(self):
        return AzureOpenAIEmbeddings(
            # model=self.AOAI_EMBEDDING_DEPLOYMENT,
            model="text-embedding-3-small",  # 1536 차원 모델로 변경
            openai_api_version=self.AOAI_API_VERSION,
            api_key=self.AOAI_API_KEY,
            azure_endpoint=self.AOAI_ENDPOINT,
        )


config = config()


def get_llm():
    """
    Azure OpenAI LLM 인스턴스 반환 메서드

    Returns:
        AzureChatOpenAI 객체
    """
    return config.get_llm()


def get_embeddings():
    """
    Azure OpenAI Embeddings 인스턴스 반환 메서드

    Returns:
        AzureOpenAIEmbeddings 객체
    """
    return config.get_embeddings()
