from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KeyPolicy:
    sequence_field: str
    output_field: str


@dataclass(frozen=True)
class EntityPolicy:
    entity: str
    own_id: str
    variable_policy: str
    blocked_variables: tuple[str, ...]
    keys: tuple[KeyPolicy, ...]
    primary_key: str


@dataclass(frozen=True)
class ForeignKeyPolicy:
    child_entity: str
    child_field: str
    parent_entity: str
    parent_field: str


@dataclass(frozen=True)
class CensusProfile:
    name: str
    source_database: str
    selection_entity: str
    identity_scope: str
    scope_field: str
    geography_entities: tuple[str, ...]
    id_fields: dict[str, str]
    entities: tuple[EntityPolicy, ...]
    foreign_keys: tuple[ForeignKeyPolicy, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


VP_PROFILE = CensusProfile(
    name="argentina-censo2022-vp",
    source_database="VP",
    selection_entity="RADIO",
    identity_scope="RADIO",
    scope_field="XRADIO",
    geography_entities=("PROV", "DPTO", "FRAC", "RADIO"),
    id_fields={
        "VIVIENDA": "XVID",
        "HOGAR": "XHID",
        "PERSONA": "XPID",
    },
    entities=(
        EntityPolicy(
            entity="VIVIENDA",
            own_id="XVID",
            variable_policy="all-stored",
            blocked_variables=(),
            keys=(KeyPolicy("XVID", "vivienda_key"),),
            primary_key="vivienda_key",
        ),
        EntityPolicy(
            entity="HOGAR",
            own_id="XHID",
            variable_policy="all-stored",
            blocked_variables=(),
            keys=(
                KeyPolicy("XHID", "hogar_key"),
                KeyPolicy("XVID", "vivienda_key"),
            ),
            primary_key="hogar_key",
        ),
        EntityPolicy(
            entity="PERSONA",
            own_id="XPID",
            variable_policy="all-stored",
            blocked_variables=("PERSONA.HNVUA",),
            keys=(
                KeyPolicy("XPID", "persona_key"),
                KeyPolicy("XHID", "hogar_key"),
                KeyPolicy("XVID", "vivienda_key"),
            ),
            primary_key="persona_key",
        ),
    ),
    foreign_keys=(
        ForeignKeyPolicy("HOGAR", "vivienda_key", "VIVIENDA", "vivienda_key"),
        ForeignKeyPolicy("PERSONA", "hogar_key", "HOGAR", "hogar_key"),
        ForeignKeyPolicy("PERSONA", "vivienda_key", "VIVIENDA", "vivienda_key"),
    ),
)
