from pydantic import BaseModel
from typing import Optional


class CountryOut(BaseModel):
    country_key: int
    iso_alpha_2: str
    iso_alpha_3: str
    country_name: str
    region: Optional[str] = None
    sub_region: Optional[str] = None
    continent: Optional[str] = None

    class Config:
        from_attributes = True


class StateOut(BaseModel):
    state_key: int
    state_code: str
    state_name: str
    is_union_territory: bool
    region: Optional[str] = None
    capital: Optional[str] = None
    is_coastal: Optional[bool] = None

    class Config:
        from_attributes = True


class HsCodeOut(BaseModel):
    hs_code_key: int
    hs_code: str
    hs_level: int
    hs_2: str
    hs_4: Optional[str] = None
    description: str
    section_name: Optional[str] = None

    class Config:
        from_attributes = True


class IngestionStatusOut(BaseModel):
    source: str
    status: Optional[str]
    last_run_at: Optional[str]
    rows_loaded: Optional[int]
    error_message: Optional[str] = None
