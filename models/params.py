from typing import Optional, Literal
from pydantic import BaseModel, Field

class QueryParams(BaseModel):
    book_id:Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    rating: Optional[int] = None
    sort_by: Optional[Literal["rating", "price", "reviews"]] = None
    sort_order: Literal["asc", "desc"] = "asc"
    page: int = Field(default=1, ge= 1)
    page_size: int = Field(default=20, ge=1, le=100)

