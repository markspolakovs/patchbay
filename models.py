import pydantic
from typing import List, Dict

class Link(pydantic.BaseModel):
    from_: str
    to: str
    class Config:
        fields = {
            "from_": "from"
        }

class StateModel(pydantic.BaseModel):
    all_links: List[Link]
    all_nodes: Dict[str, Dict[str, Dict[str, str]]]
