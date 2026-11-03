"""Read-only LangChain tools with strict argument schemas and domain validation."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from langchain.tools import tool


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class CatalogArguments(Arguments):
    query: str | None = Field(default=None, min_length=1, max_length=200, description='Nome, marca ou modelo mencionado pelo cliente, sem a pergunta completa. Ex.: Takamine GD20.')
    category_id: int | None = None
    min_price: str | None = None
    max_price: str | None = None
    in_stock: bool = True
    status: Literal['active', 'inactive'] = 'active'
    limit: int = Field(default=4, ge=1, le=10)
    offset: int = Field(default=0, ge=0)


class ComparisonArguments(Arguments):
    product_ids: list[int] = Field(min_length=2, max_length=4)
    budget: str | None = None


class PolicyArguments(Arguments):
    query: str = Field(min_length=1, max_length=500)


class ContactArguments(Arguments):
    channel: Literal['all', 'remote', 'store'] = 'all'


class PromotionArguments(Arguments):
    product_id: int | None = None
    category_id: int | None = None
    max_price: str | None = None
    limit: int = Field(default=4, ge=1, le=10)
    offset: int = Field(default=0, ge=0)


SCHEMAS: dict[str, type[BaseModel]] = {
    'dismiss_budget_offer': Arguments,
    'search_catalog': CatalogArguments,
    'list_categories': Arguments,
    'compare_products': ComparisonArguments,
    'search_policies': PolicyArguments,
    'store_contacts': ContactArguments,
    'search_promotions': PromotionArguments,
}


def build_tools(dispatch, definitions):
    registry = {}
    for definition in definitions:
        name = definition['name']

        def execute(_name=name, **kwargs):
            return dispatch(_name, {key: value for key, value in kwargs.items() if value is not None})

        registry[name] = tool(name, description=definition['description'],
                              args_schema=SCHEMAS[name])(execute)
    return registry
