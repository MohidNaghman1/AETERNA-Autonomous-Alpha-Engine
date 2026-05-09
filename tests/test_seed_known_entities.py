from pathlib import Path

import pytest

from scripts.seed_known_entities import (
    _profile_confidence,
    load_seed_entities,
    normalize_entity_type,
    normalize_wallet,
)


def test_load_seed_entities_groups_wallets_by_entity(tmp_path: Path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "\n".join(
            [
                "entity_id,name,entity_type,wallet_address,verified,verification_sources,reliability_score",
                "ent_coinbase,Coinbase,cex,0x0000000000000000000000000000000000000001,true,etherscan;manual,0.9",
                "ent_coinbase,Coinbase,exchange,0x0000000000000000000000000000000000000002,true,dune,0.9",
            ]
        ),
        encoding="utf-8",
    )

    entities = load_seed_entities(csv_path)

    assert list(entities) == ["ent_coinbase"]
    entity = entities["ent_coinbase"]
    assert entity.entity_type == "exchange"
    assert entity.wallets == {
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
    }
    assert entity.verification_sources == {"etherscan", "manual", "dune"}


def test_normalize_wallet_rejects_bad_address():
    with pytest.raises(ValueError):
        normalize_wallet("0xnot-an-address")


def test_normalize_entity_type_rejects_unknown_label():
    with pytest.raises(ValueError):
        normalize_entity_type("hedge_fund")


def test_profile_confidence_preserves_explicit_zero_reliability(tmp_path: Path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "\n".join(
            [
                "entity_id,name,entity_type,wallet_address,verified,reliability_score",
                "ent_zero,Zero Trust,whale,0x0000000000000000000000000000000000000003,false,0.0",
            ]
        ),
        encoding="utf-8",
    )

    entities = load_seed_entities(csv_path)

    assert entities["ent_zero"].reliability_score == 0.0
    assert _profile_confidence(entities["ent_zero"]) == 0.0


def test_load_seed_entities_normalizes_cex_alias(tmp_path: Path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "\n".join(
            [
                "entity_id,name,entity_type,wallet_address",
                "ent_exchange,CEX Wallet,cex,0x0000000000000000000000000000000000000004",
            ]
        ),
        encoding="utf-8",
    )

    entities = load_seed_entities(csv_path)

    assert entities["ent_exchange"].entity_type == "exchange"
