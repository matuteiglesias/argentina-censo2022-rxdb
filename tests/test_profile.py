import json

from argentina_censo2022_rxdb.cli import main
from argentina_censo2022_rxdb.controls import PERMANENT_LABORATORIES
from argentina_censo2022_rxdb.profile import VP_FRAC_PROFILE, VP_PROFILE


def test_vp_profile_keeps_domain_policy_outside_generic_core():
    assert VP_PROFILE.selection_entity == "RADIO"
    assert VP_PROFILE.identity_scope == "RADIO"
    assert VP_PROFILE.scope_field == "XRADIO"
    assert VP_PROFILE.parent_map["RADIO"] == "FRAC"
    assert VP_PROFILE.parent_map["VIVIENDA"] == "RADIO"
    assert VP_PROFILE.parent_map["HOGAR"] == "VIVIENDA"
    assert VP_PROFILE.parent_map["PERSONA"] == "HOGAR"
    assert VP_PROFILE.id_fields == {
        "VIVIENDA": "XVID",
        "HOGAR": "XHID",
        "PERSONA": "XPID",
    }
    persona = next(policy for policy in VP_PROFILE.entities if policy.entity == "PERSONA")
    assert persona.variable_policy == "all-stored"
    assert persona.blocked_variables == ("PERSONA.HNVUA",)
    assert persona.primary_key == "persona_key"
    assert len(VP_PROFILE.foreign_keys) == 3


def test_frac_profile_changes_partition_only_not_record_identity():
    assert VP_FRAC_PROFILE.selection_entity == "FRAC"
    assert VP_FRAC_PROFILE.identity_scope == "RADIO"
    assert VP_FRAC_PROFILE.scope_field == "XRADIO"
    assert VP_FRAC_PROFILE.id_fields == VP_PROFILE.id_fields
    assert VP_FRAC_PROFILE.entities == VP_PROFILE.entities
    assert VP_FRAC_PROFILE.foreign_keys == VP_PROFILE.foreign_keys


def test_permanent_laboratories_include_m3_radio_and_frac():
    assert PERMANENT_LABORATORIES["relational_radio"]["selection_code"] == "061471101"
    assert PERMANENT_LABORATORIES["relational_radio"]["counts"] == {
        "VIVIENDA": 73,
        "HOGAR": 56,
        "PERSONA": 137,
    }
    assert PERMANENT_LABORATORIES["frac"]["counts"]["PERSONA"] == 173


def test_cli_profiles_are_machine_readable(capsys):
    assert main(["profile", "vp"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "argentina-censo2022-vp"
    assert payload["source_database"] == "VP"
    assert payload["parent_map"]["PERSONA"] == "HOGAR"

    assert main(["profile", "vp-frac"]) == 0
    frac = json.loads(capsys.readouterr().out)
    assert frac["name"] == "argentina-censo2022-vp-frac"
    assert frac["selection_entity"] == "FRAC"
    assert frac["identity_scope"] == "RADIO"
