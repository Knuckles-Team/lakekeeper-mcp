"""Pydantic models for Lakekeeper (Iceberg REST catalog) operations."""

from pydantic import BaseModel, Field


class NamespaceRef(BaseModel):
    """One Iceberg namespace within a warehouse."""

    warehouse: str = Field(default="", description="Warehouse name (default from env if omitted).")
    namespace: str = Field(description="Namespace name, e.g. 'analytics'.")


class TableRef(BaseModel):
    """One Iceberg table within a namespace."""

    warehouse: str = Field(default="", description="Warehouse name (default from env if omitted).")
    namespace: str = Field(description="Namespace name, e.g. 'analytics'.")
    table: str = Field(description="Table name, e.g. 'trino_verify'.")


class OwnershipClassification(BaseModel):
    """A table's ownership classification per GOC-78's single-writer rule."""

    warehouse: str = Field(default="")
    namespace: str = Field(description="Namespace name.")
    table: str = Field(description="Table name.")
    owner: str = Field(
        description=(
            "One of 'engine' (eg redb is authoritative, DEC-CA-01 projection-only) "
            "or 'lakekeeper-native' (Spark/Trino-written, Lakekeeper's own metadata "
            "is authoritative)."
        )
    )
