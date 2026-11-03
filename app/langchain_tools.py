"""Read-only LangChain tools with strict argument schemas and domain validation."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from langchain.tools import tool


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class CatalogArguments(Arguments):
    query: str | None = Field(default=None, min_length=1, max_length=200, description='Somente nome, marca ou modelo específico. Não use tipo de instrumento como query; categorias usam category_id/category_ids.')
    category_id: int | None = Field(default=None, gt=0, description='ID real de UMA categoria. Use somente se o pedido atual nomeia um tipo específico ou se refere explicitamente às opções anteriores. Um pedido genérico por instrumentos remove a categoria antiga: use category_ids=[]. Nunca adivinhe IDs.')
    category_ids: list[int] | None = Field(default=None, max_length=9, description='IDs reais de VÁRIAS categorias (união). Use [] para pedido genérico de instrumentos, mesmo se antes havia uma categoria específica. Não manter categoria antiga nesses pedidos. Não combinar com category_id.')
    min_price: str | None = None
    max_price: str | None = None
    in_stock: bool = True
    status: Literal['active', 'inactive'] = 'active'
    limit: int = Field(default=4, ge=1, le=10)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def unique_scope(self):
        if self.category_id is not None and self.category_ids is not None:
            raise ValueError('Use category_id ou category_ids, não ambos.')
        if self.category_ids is not None and (any(i <= 0 for i in self.category_ids) or len(set(self.category_ids)) != len(self.category_ids)):
            raise ValueError('Use IDs positivos, sem duplicatas.')
        return self


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
