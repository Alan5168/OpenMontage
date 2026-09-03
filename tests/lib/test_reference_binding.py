"""Experimental reference dialect — not a production identity policy."""

from lib.h3_context_ir import compile_h3_ir
from lib.reference_binding import (
    CHARACTER_DO_NOT_INHERIT,
    CHARACTER_INHERIT,
    EXPERIMENTAL_DIALECT,
    PRODUCTION_POLICY,
    UNVERIFIED_DEFAULTS,
    annotate_packed_role,
    bindings_from_owner,
    compile_bindings_stanza,
    defaults_for_role,
)
from lib.seedance_ref_packer import pack_seedance_refs


def test_module_is_experimental_not_policy():
    assert EXPERIMENTAL_DIALECT is True
    assert PRODUCTION_POLICY is False


def test_character_identity_defaults_match_nine_ref_teacher():
    inherit, banned = defaults_for_role("CHARACTER_IDENTITY")
    assert inherit == CHARACTER_INHERIT
    assert banned == CHARACTER_DO_NOT_INHERIT


def test_scene_prop_defaults_are_unverified_and_not_attached():
    assert "SCENE_REFERENCE" in UNVERIFIED_DEFAULTS
    packed = annotate_packed_role(
        {"role": "SCENE_REFERENCE", "path": "bible/kitchen/wide.png"},
        experimental=True,
    )
    assert "inherit" not in packed
    ident = annotate_packed_role(
        {"role": "IDENTITY_REFERENCE", "path": "bible/avery/sheet.png"},
        owner="Avery",
        experimental=True,
    )
    assert ident["inherit"] == list(CHARACTER_INHERIT)


def test_stanza_does_not_call_identity_still_picture_1():
    bindings = bindings_from_owner(
        owner="Avery",
        still_refs=["bible/avery/sheet.png"],
    )
    text = compile_bindings_stanza(bindings)
    assert text.startswith("[experimental_reference_binding]")
    assert "REF_1 is CHARACTER_IDENTITY owned by Avery only" in text
    assert "Picture 1" not in text
    assert "sheet.png" not in text


def test_h3_ir_does_not_emit_stanza_without_opt_in():
    out = compile_h3_ir(
        {
            "overview": "MCU hold",
            "duration_seconds": 5,
            "identity": {
                "name": "Avery",
                "must": ["black hoodie"],
                "reference_bindings": bindings_from_owner(
                    owner="Avery",
                    still_refs=["bible/avery/sheet.png"],
                ),
            },
        }
    )
    assert "experimental_reference_binding" not in out["prompt"]
    assert "Do not inherit sheet background" not in out["prompt"]


def test_h3_ir_emits_binding_stanza_when_opted_in():
    out = compile_h3_ir(
        {
            "overview": "MCU hold",
            "duration_seconds": 5,
            "experimental_reference_binding": True,
            "identity": {
                "name": "Avery",
                "must": ["black hoodie"],
                "reference_bindings": bindings_from_owner(
                    owner="Avery",
                    still_refs=["bible/avery/sheet.png"],
                ),
            },
        }
    )
    assert "[experimental_reference_binding]" in out["prompt"]
    assert "CHARACTER_IDENTITY owned by Avery only" in out["prompt"]
    assert out["mode"] == "i2va"
    assert "sheet.png" not in out["prompt"]


def test_seedance_packer_stays_off_without_flag():
    packed = pack_seedance_refs(
        {
            "character_variant": {
                "character_id": "jesse",
                "still_refs": ["bible/jesse/sheets/kitchen_3q.png"],
            },
            "anchor_bindings": [
                {"role": "SCENE_REFERENCE", "path": "bible/kitchen/wide.png"}
            ],
        }
    )
    assert all("do_not_inherit" not in row for row in packed["roles"])
