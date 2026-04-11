from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "items-service"
    app_env: str = "local"

    gcp_project_id: str

    # Keep names different from your existing env vars to avoid collisions.
    firestore_items_collection_service: str = "items_catalog_v2"

    vertex_search_location_service: str = "global"
    vertex_search_items_datastore_id_service: str = "items-datastore-v2"

    # Freshness decay for business score: age in days where score becomes 0.5.
    freshness_halflife_days: float = 180.0
    # Image upload bucket
    gcp_storage_bucket_images: str = "blog-images-default-bucket"

@lru_cache
def get_settings() -> Settings:
    return Settings()
