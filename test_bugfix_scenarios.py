#!/usr/bin/env python3
"""
Tests for bug fixes:
  TODO 01 — after_art timing in combat_mixin.py
  TODO 02 — return_cheer_and_draw draw formula in card_movement.py
  TODO 03 — public zone hidden_info in action_handler_mixin.py
  TODO 04 — on_kill_effects field migration (hBP07-027, hSD10-006)
"""

import sys
import random
from copy import deepcopy
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "app"))

from app.card_database import CardDatabase
from app.gameengine import GameEngine
from app.engine.constants import DecisionType, EventType, GameOverReason
from app.engine.models import GameAction
from app.engine.helpers import add_ids_to_effects


def make_cheer_deck():
    return {
        "hY02-001": 8,
        "hY03-001": 8,
        "hY05-001": 4,
    }


def make_custom_engine(p1_deck, p2_deck, oshi_p1="hBP07-004", oshi_p2="hBP01-001"):
    card_db = CardDatabase()
    p1_info = {
        "player_id": "p1",
        "username": "p1",
        "oshi_id": oshi_p1,
        "deck": p1_deck,
        "cheer_deck": make_cheer_deck(),
    }
    p2_info = {
        "player_id": "p2",
        "username": "p2",
        "oshi_id": oshi_p2,
        "deck": p2_deck,
        "cheer_deck": make_cheer_deck(),
    }
    engine = GameEngine(card_db, "versus", [p1_info, p2_info])
    engine.blank_continuation = lambda: None
    engine.random_gen = random.Random(0)
    return engine


def take_card(player, card_id):
    for i, card in enumerate(player.deck):
        if card["card_id"] == card_id:
            return player.deck.pop(i)
    raise ValueError(f"Card not found in deck: {card_id}")


def take_cheer(player, cheer_id):
    for i, card in enumerate(player.cheer_deck):
        if card["card_id"] == cheer_id:
            return player.cheer_deck.pop(i)
    raise ValueError(f"Cheer not found in cheer deck: {cheer_id}")


def resolve_all_decisions(engine, chooser="non_pass"):
    while engine.current_decision:
        decision = engine.current_decision
        player_id = decision["decision_player"]
        decision_type = decision["decision_type"]

        if decision_type == DecisionType.DecisionChoice:
            idx = decision["min_choice"]
            if chooser == "non_pass":
                for i, choice in enumerate(decision.get("choice", [])):
                    if choice.get("effect_type") != "pass":
                        idx = i
                        break
            engine.handle_game_message(
                player_id,
                GameAction.EffectResolution_MakeChoice,
                {"choice_index": idx},
            )
            continue

        if decision_type == DecisionType.DecisionEffect_MoveCheerBetweenHolomems:
            amount = max(decision.get("amount_min", 0), 0)
            available_cheer = list(decision.get("available_cheer", []))
            available_targets = list(decision.get("available_targets", []))
            placements = {}
            if amount > 0 and available_cheer and available_targets:
                target = available_targets[0]
                for cheer_id in available_cheer[:amount]:
                    placements[cheer_id] = target
            engine.handle_game_message(
                player_id,
                GameAction.EffectResolution_MoveCheerBetweenHolomems,
                {"placements": placements},
            )
            continue

        if decision_type == DecisionType.DecisionEffect_ChooseCardsForEffect:
            amount = max(decision.get("amount_min", 0), 0)
            card_ids = list(decision.get("cards_can_choose", []))[:amount]
            engine.handle_game_message(
                player_id,
                GameAction.EffectResolution_ChooseCardsForEffect,
                {"card_ids": card_ids},
            )
            continue

        if decision_type == DecisionType.DecisionEffect_OrderCards:
            card_ids = list(decision.get("card_ids", []))
            engine.handle_game_message(
                player_id,
                GameAction.EffectResolution_OrderCards,
                {"card_ids": card_ids},
            )
            continue

        raise RuntimeError(f"Unhandled decision type in resolver: {decision_type}")


# ---------------------------------------------------------------------------
# TODO 01 — after_art timing: verify that after_art effects actually execute
# ---------------------------------------------------------------------------
def scenario_hbp07_035_after_art_effects_execute():
    """hBP07-035 surging_exhaust: after_art return_cheer_and_draw should trigger."""
    engine = make_custom_engine(
        p1_deck={"hBP07-035": 1, "hBP07-032": 10},
        p2_deck={"hBP07-036": 10},
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")
    p1.oshi_card["effects"] = []
    p2.oshi_card["effects"] = []

    performer = take_card(p1, "hBP07-035")
    filler = take_card(p2, "hBP07-036")
    p1.center = [performer]
    p2.center = [filler]
    p2.backstage = [take_card(p2, "hBP07-036")]
    engine.active_player_id = "p1"

    # Attach 2 green cheer
    performer["attached_cheer"].append(take_cheer(p1, "hY02-001"))
    performer["attached_cheer"].append(take_cheer(p1, "hY02-001"))

    # Set target HP high so it doesn't die
    filler["hp"] = 500
    filler["damage"] = 0

    hand_before = len(p1.hand)

    engine.begin_perform_art(
        performer["game_card_id"],
        "surging_exhaust",
        filler["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)

    cheer_on_performer = len(performer.get("attached_cheer", []))
    hand_after = len(p1.hand)
    draws = hand_after - hand_before

    assert cheer_on_performer == 0, (
        f"after_art should return all cheer; {cheer_on_performer} remain")
    assert draws == 2, (
        f"after_art return_cheer_and_draw should draw 2; drew {draws}")
    assert filler["damage"] > 0, (
        f"Damage should have been dealt after after_art effects")


# ---------------------------------------------------------------------------
# TODO 02 — return_cheer_and_draw: draw count must equal returned count
# ---------------------------------------------------------------------------
def scenario_hbp07_035_draw_equals_returned_count():
    """Draw count must be returned_count, not max(0, returned - hand_size)."""
    engine = make_custom_engine(
        p1_deck={"hBP07-035": 1, "hBP07-032": 20},
        p2_deck={"hBP07-036": 10},
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")
    p1.oshi_card["effects"] = []
    p2.oshi_card["effects"] = []

    performer = take_card(p1, "hBP07-035")
    filler = take_card(p2, "hBP07-036")
    p1.center = [performer]
    p2.center = [filler]
    p2.backstage = [take_card(p2, "hBP07-036")]
    engine.active_player_id = "p1"

    # Put 5 cards in hand so old formula would reduce draws
    for _ in range(5):
        p1.hand.append(take_card(p1, "hBP07-032"))

    # Attach 3 cheer
    performer["attached_cheer"].append(take_cheer(p1, "hY02-001"))
    performer["attached_cheer"].append(take_cheer(p1, "hY02-001"))
    performer["attached_cheer"].append(take_cheer(p1, "hY02-001"))

    filler["hp"] = 500
    filler["damage"] = 0

    hand_before = len(p1.hand)

    engine.begin_perform_art(
        performer["game_card_id"],
        "surging_exhaust",
        filler["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)

    hand_after = len(p1.hand)
    draws = hand_after - hand_before

    # Old buggy formula: max(0, 3 - 5) = 0 draws
    # Fixed formula: 3 draws
    assert draws == 3, (
        f"Expected 3 draws (returned_count), got {draws}. "
        f"Old formula max(0,3-{hand_before})=0 may still be in effect")


# ---------------------------------------------------------------------------
# TODO 03 — public zone hidden_info: backstage → deck must not hide card_id
# ---------------------------------------------------------------------------
def scenario_hbp07_004_backstage_to_deck_not_hidden():
    """choose_cards from backstage to bottom_of_deck must not hide card_id."""
    engine = make_custom_engine(
        p1_deck={"hBP07-036": 10, "hBP07-037": 2},
        p2_deck={"hBP07-036": 10},
        oshi_p1="hBP07-004",
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")
    p2.oshi_card["effects"] = []

    debut = take_card(p1, "hBP07-036")
    p1.center = [take_card(p1, "hBP07-036")]
    p1.backstage = [debut]
    p2.center = [take_card(p2, "hBP07-036")]
    engine.active_player_id = "p1"

    target_game_card_id = debut["game_card_id"]

    effect = deepcopy({
        "effect_type": "choose_cards",
        "from": "backstage",
        "look_at": -1,
        "destination": "bottom_of_deck",
        "amount_min": 1,
        "amount_max": 1,
        "requirement": "holomem_debut",
        "requirement_names": ["akai_haato"],
        "remaining_cards_action": "nothing",
    })
    add_ids_to_effects([effect], "p1", p1.oshi_card["game_card_id"])

    events_before = len(engine.all_events)
    engine.begin_resolving_effects([effect], engine.blank_continuation)
    resolve_all_decisions(engine)

    move_events = [
        e for e in engine.all_events[events_before:]
        if e.get("event_type") == EventType.EventType_MoveCard
        and e.get("card_id") == target_game_card_id
    ]
    assert move_events, "Expected at least one MoveCard event for the debut card"

    for me in move_events:
        assert "hidden_info_player" not in me, (
            f"MoveCard from backstage (public zone) must NOT have hidden_info_player; "
            f"got {me}")


# ---------------------------------------------------------------------------
# TODO 04 — on_kill_effects field: hBP07-027 draw 1 on kill
# ---------------------------------------------------------------------------
def scenario_hbp07_027_on_kill_effects_draw():
    """hBP07-027 on_kill_effects (draw 1) must trigger when target is downed."""
    engine = make_custom_engine(
        p1_deck={"hBP07-027": 1, "hBP07-023": 10},
        p2_deck={"hBP07-036": 10},
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")
    p1.oshi_card["effects"] = []
    p2.oshi_card["effects"] = []

    attacker = take_card(p1, "hBP07-027")
    defender = take_card(p2, "hBP07-036")
    spare_back = take_card(p2, "hBP07-036")
    p1.center = [attacker]
    p2.center = [defender]
    p2.backstage = [spare_back]
    p2.life = [take_cheer(p2, "hY02-001"), take_cheer(p2, "hY03-001")]
    engine.active_player_id = "p1"

    # Art cost: 2 green. Attach cheer (not deducted in direct begin_perform_art call).
    attacker["attached_cheer"].append(take_cheer(p1, "hY02-001"))
    attacker["attached_cheer"].append(take_cheer(p1, "hY02-001"))

    # Set defender damage so art power (70) will down it.
    defender_hp = p2.get_card_hp(defender)
    defender["damage"] = defender_hp - 1

    hand_before = len(p1.hand)

    engine.begin_perform_art(
        attacker["game_card_id"],
        "jouounoheikatoyobare",
        defender["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)

    hand_after = len(p1.hand)
    draws = hand_after - hand_before

    assert draws == 1, (
        f"on_kill_effects should draw 1 card; drew {draws}")
    assert not engine.is_game_over(), (
        "Game should not end — P2 still has life remaining")


# ---------------------------------------------------------------------------
# TODO 04b — on_kill_effects field: hSD10-006 send_cheer on kill
# ---------------------------------------------------------------------------
def scenario_hsd10_006_on_kill_effects_send_cheer():
    """hSD10-006 accelera_beat_blaze on_kill_effects (send_cheer) must trigger on center KO."""
    engine = make_custom_engine(
        p1_deck={"hSD10-006": 1, "hSD10-002": 10},
        p2_deck={"hBP07-036": 10},
        oshi_p1="hSD10-001",
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")
    p1.oshi_card["effects"] = []
    p2.oshi_card["effects"] = []

    attacker = take_card(p1, "hSD10-006")
    defender = take_card(p2, "hBP07-036")
    spare_back = take_card(p2, "hBP07-036")
    p1.center = [attacker]
    backstage_mem = take_card(p1, "hSD10-002")
    p1.backstage = [backstage_mem]
    p2.center = [defender]
    p2.backstage = [spare_back]
    p2.life = [take_cheer(p2, "hY02-001"), take_cheer(p2, "hY03-001")]
    engine.active_player_id = "p1"

    attacker["attached_cheer"].append(take_cheer(p1, "hY02-001"))
    attacker["attached_cheer"].append(take_cheer(p1, "hY02-001"))
    attacker["attached_cheer"].append(take_cheer(p1, "hY02-001"))

    # Ensure defender is white (condition: target_color white gives +50 in before_art)
    defender["colors"] = ["white"]
    defender_hp = p2.get_card_hp(defender)
    # Set damage so art (140 base + 50 if white = 190) will down it
    defender["damage"] = defender_hp - 1

    backstage_cheer_before = len(backstage_mem.get("attached_cheer", []))

    engine.begin_perform_art(
        attacker["game_card_id"],
        "accelera_beat_blaze",
        defender["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)

    backstage_cheer_after = len(backstage_mem.get("attached_cheer", []))
    cheer_gained = backstage_cheer_after - backstage_cheer_before

    assert cheer_gained > 0, (
        f"on_kill_effects send_cheer should attach cheer to backstage; "
        f"gained {cheer_gained}")
    assert not engine.is_game_over(), (
        "Game should not end — P2 still has life remaining")


# ---------------------------------------------------------------------------

def main():
    scenarios = [
        ("TODO01: hBP07-035 after_art effects execute",
         scenario_hbp07_035_after_art_effects_execute),
        ("TODO02: hBP07-035 draw = returned_count (formula fix)",
         scenario_hbp07_035_draw_equals_returned_count),
        ("TODO03: hBP07-004 backstage→deck not HIDDEN",
         scenario_hbp07_004_backstage_to_deck_not_hidden),
        ("TODO04: hBP07-027 on_kill_effects draw",
         scenario_hbp07_027_on_kill_effects_draw),
        ("TODO04b: hSD10-006 on_kill_effects send_cheer",
         scenario_hsd10_006_on_kill_effects_send_cheer),
    ]

    passed = 0
    for name, fn in scenarios:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")

    print(f"\nResult: {passed}/{len(scenarios)} passed")
    return 0 if passed == len(scenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
