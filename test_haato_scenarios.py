#!/usr/bin/env python3
import sys
from copy import deepcopy
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "app"))

from app.card_database import CardDatabase
from app.gameengine import GameEngine
from app.engine.constants import DecisionType, EventType, GameOverReason
from app.engine.models import GameAction
from app.engine.helpers import add_ids_to_effects


def make_deck():
    return {
        "hBP03-031": 39,
        "hBP07-036": 3,
        "hBP07-037": 2,
        "hBP07-039": 1,
        "hBP07-042": 1,
        "hBP03-033": 1,
        "hBP03-095": 2,
        "hBP01-114": 1,
    }


def make_cheer_deck():
    return {
        "hY02-001": 4,
        "hY03-001": 8,
        "hY05-001": 4,
        "hY06-001": 4,
    }


def make_engine(oshi_p1="hBP07-004", oshi_p2="hBP01-001"):
    card_db = CardDatabase()
    p1_info = {
        "player_id": "p1",
        "username": "p1",
        "oshi_id": oshi_p1,
        "deck": make_deck(),
        "cheer_deck": make_cheer_deck(),
    }
    p2_info = {
        "player_id": "p2",
        "username": "p2",
        "oshi_id": oshi_p2,
        "deck": make_deck(),
        "cheer_deck": make_cheer_deck(),
    }
    engine = GameEngine(card_db, "versus", [p1_info, p2_info])
    engine.blank_continuation = lambda: None
    return engine


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


def scenario_hbp07_004_draw2_on_own_move():
    engine = make_engine(oshi_p1="hBP07-004")
    p1 = engine.get_player("p1")
    engine.active_player_id = "p1"

    center = take_card(p1, "hBP07-036")
    backstage = take_card(p1, "hBP07-037")
    p1.center = [center]
    p1.backstage = [backstage]

    p1.hand = []
    p1.deck.insert(0, take_card(p1, "hBP03-031"))
    p1.deck.insert(0, take_card(p1, "hBP03-031"))

    engine.effect_context_stack.append({"player_id": "p1", "source_card_id": center["game_card_id"]})
    p1.move_card(backstage["game_card_id"], "deck")
    engine.effect_context_stack.pop()
    resolve_all_decisions(engine)

    assert len(p1.hand) == 2, f"Expected draw 2, got hand={len(p1.hand)}"


def scenario_hbp07_039_gift_once_per_turn():
    engine = make_engine(oshi_p1="hBP07-004")
    p1 = engine.get_player("p1")
    engine.active_player_id = "p1"

    gift_holder = take_card(p1, "hBP07-039")
    moved1 = take_card(p1, "hBP07-036")
    moved2 = take_card(p1, "hBP07-037")
    p1.center = [gift_holder]
    p1.backstage = [moved1, moved2]

    yellow1 = take_cheer(p1, "hY06-001")
    yellow2 = take_cheer(p1, "hY06-001")
    p1.archive.insert(0, yellow1)

    p1.move_card(moved1["game_card_id"], "deck")
    resolve_all_decisions(engine, chooser="non_pass")

    attached_after_first = [c for c in gift_holder["attached_cheer"] if c["card_id"] == "hY06-001"]
    assert len(attached_after_first) == 1, "Expected first gift trigger to attach one yellow cheer"

    p1.archive.insert(0, yellow2)
    p1.move_card(moved2["game_card_id"], "deck")
    resolve_all_decisions(engine, chooser="non_pass")

    attached_after_second = [c for c in gift_holder["attached_cheer"] if c["card_id"] == "hY06-001"]
    archive_yellow = [c for c in p1.archive if c["card_id"] == "hY06-001"]
    assert len(attached_after_second) == 1, "Gift should not trigger twice in one turn"
    assert len(archive_yellow) == 1, "Second yellow cheer should remain in archive"


def scenario_hbp03_033_tool_damage_10_or_30():
    engine = make_engine()
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")

    p1.oshi_card["effects"] = []
    p2.oshi_card["effects"] = []

    attacker = take_card(p1, "hBP03-033")
    defender = take_card(p2, "hBP07-036")
    p1.center = [attacker]
    p2.center = [defender]
    engine.active_player_id = "p1"

    effect = deepcopy(attacker["bloom_effects"][0])
    add_ids_to_effects([effect], "p1", attacker["game_card_id"])

    defender["damage"] = 0
    engine.begin_resolving_effects([effect], engine.blank_continuation)
    resolve_all_decisions(engine)
    no_tool_damage = defender["damage"]

    defender["damage"] = 0
    tool = take_card(p2, "hBP01-114")
    defender["attached_support"].append(tool)
    effect2 = deepcopy(attacker["bloom_effects"][0])
    add_ids_to_effects([effect2], "p1", attacker["game_card_id"])
    engine.begin_resolving_effects([effect2], engine.blank_continuation)
    resolve_all_decisions(engine)
    with_tool_damage = defender["damage"]

    assert no_tool_damage == 10, f"Expected 10 damage without tool, got {no_tool_damage}"
    assert with_tool_damage == 30, f"Expected 30 damage with tool, got {with_tool_damage}"


def scenario_hbp07_042_second_art_bonus_on_stage_to_deck_this_turn():
    engine = make_engine()
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")
    p1.oshi_card["effects"] = []
    p2.oshi_card["effects"] = []

    performer = take_card(p1, "hBP07-042")
    moved_card = take_card(p1, "hBP07-036")
    target = take_card(p2, "hBP07-042")

    p1.center = [performer]
    p1.backstage = [moved_card]
    p2.center = [target]
    engine.active_player_id = "p1"

    for _ in range(3):
        performer["attached_cheer"].append(take_cheer(p1, "hY03-001"))

    target["damage"] = 0
    engine.begin_perform_art(
        performer["game_card_id"],
        "shiawase_heno_tabiji",
        target["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)
    damage_without_move = target["damage"]

    target["damage"] = 0
    p1.move_card(moved_card["game_card_id"], "deck")
    resolve_all_decisions(engine)
    engine.begin_perform_art(
        performer["game_card_id"],
        "shiawase_heno_tabiji",
        target["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)
    damage_with_move = target["damage"]

    assert damage_without_move == 140, f"Expected 140 without turn move condition, got {damage_without_move}"
    assert damage_with_move == 190, f"Expected 190 with turn move condition, got {damage_with_move}"


def scenario_hbp07_004_cheer_step_attach_does_not_lose_game():
    engine = make_engine(oshi_p1="hBP07-004")
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")

    p1.center = [take_card(p1, "hBP07-036")]
    p2.center = [take_card(p2, "hBP07-036")]
    p1.first_turn = False
    p2.first_turn = False
    engine.active_player_id = "p1"

    engine.begin_player_turn(False)
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionPlaceCheer

    cheer_id = engine.current_decision["cheer_to_place"][0]
    target_id = p1.center[0]["game_card_id"]
    engine.handle_game_message(
        "p1",
        GameAction.PlaceCheer,
        {"placements": {cheer_id: target_id}},
    )

    assert not engine.is_game_over(), "Cheer step attach should not end the game"
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionMainStep
    assert len(p1.center[0]["attached_cheer"]) == 1, "Cheer should be attached to center"


def scenario_hsd12_007_on_kill_choose_archive_does_not_crash():
    engine = make_custom_engine(
        p1_deck={
            "hSD12-007": 1,
            "hBP05-074": 1,
            "hBP05-075": 1,
        },
        p2_deck={
            "hSD13-006": 1,
            "hBP07-036": 1,
        },
        oshi_p1="hSD12-001",
        oshi_p2="hSD13-001",
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")

    attacker = take_card(p1, "hSD12-007")
    defender = take_card(p2, "hSD13-006")
    spare_back = take_card(p2, "hBP07-036")
    support_a = take_card(p1, "hBP05-074")
    support_b = take_card(p1, "hBP05-075")

    p1.center = [attacker]
    p2.center = [defender]
    p2.backstage = [spare_back]
    p2.life = [take_cheer(p2, "hY02-001"), take_cheer(p2, "hY03-001")]

    # Leave one extra support card in archive so there are remaining cards
    # after selecting one on-kill target from archive.
    p1.archive = [support_a, support_b]

    # Ensure the art downs the target.
    defender["damage"] = p2.get_card_hp(defender) - 1

    engine.active_player_id = "p1"
    engine.begin_perform_art(
        attacker["game_card_id"],
        "dont_underestimate_us",
        defender["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)

    assert not engine.is_game_over(), "on_kill choose from archive should not end game by internal error"
    assert any(card["card_id"] == "hBP05-074" for card in p1.hand), "Expected hBP05-074 to move archive -> hand"
    assert any(card["card_id"] == "hBP05-075" for card in p1.archive), "Expected unchosen archive card to remain in archive"


def scenario_hsd13_001_oshi_choose_archive_stage_does_not_crash():
    engine = make_custom_engine(
        p1_deck={
            "hSD13-006": 1,
            "hSD13-007": 1,
        },
        p2_deck={
            "hBP07-036": 1,
        },
        oshi_p1="hSD13-001",
        oshi_p2="hBP01-001",
    )
    p1 = engine.get_player("p1")

    justice_a = take_card(p1, "hSD13-006")
    justice_b = take_card(p1, "hSD13-007")
    p1.archive = [justice_a, justice_b]

    effect = deepcopy(p1.oshi_card["actions"][0]["effects"][1])
    add_ids_to_effects([effect], "p1", p1.oshi_card["game_card_id"])
    engine.begin_resolving_effects([effect], engine.blank_continuation)
    resolve_all_decisions(engine)

    assert not engine.is_game_over(), "oshi choose_cards archive->stage should not end game by internal error"
    stage_ids = {card["card_id"] for card in p1.get_holomem_on_stage()}
    assert stage_ids & {"hSD13-006", "hSD13-007"}, "Expected one #Justice holomem to move archive -> stage"
    archive_ids = [card["card_id"] for card in p1.archive]
    assert len([cid for cid in archive_ids if cid in ["hSD13-006", "hSD13-007"]]) == 1, "Expected one unchosen #Justice holomem to remain in archive"


def scenario_internal_error_ends_game_neutral():
    engine = make_engine()

    def _raise_internal_error(_player_id, _action_data):
        raise RuntimeError("forced_internal_error_for_test")

    engine.handle_mulligan = _raise_internal_error
    engine.handle_game_message("p1", GameAction.Mulligan, {"do_mulligan": False})

    assert engine.is_game_over(), "Internal action exception should end the game"
    assert engine.game_over_event.get("reason_id") == GameOverReason.GameOverReason_InternalError
    assert engine.game_over_event.get("winner_id") == ""
    assert engine.game_over_event.get("loser_id") == ""

    game_error_events = [e for e in engine.all_events if e.get("event_type") == EventType.EventType_GameError]
    game_over_events = [e for e in engine.all_events if e.get("event_type") == EventType.EventType_GameOver]
    assert game_error_events, "Internal error should emit game_error event"
    assert game_over_events, "Internal error should emit neutral game_over event"


def scenario_hsd12_015_not_global_limited_but_once_per_turn_by_name():
    engine = make_custom_engine(
        p1_deck={
            "hSD12-003": 1,
            "hSD12-015": 2,
            "hBP01-110": 1,
        },
        p2_deck={
            "hBP07-036": 1,
        },
        oshi_p1="hSD12-001",
        oshi_p2="hBP01-001",
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")

    advent_center = take_card(p1, "hSD12-003")
    p1.center = [advent_center]
    p2.center = [take_card(p2, "hBP07-036")]

    escape_a = take_card(p1, "hSD12-015")
    escape_b = take_card(p1, "hSD12-015")
    other_limited = take_card(p1, "hBP01-110")
    p1.hand = [escape_a, escape_b, other_limited]

    p1.archive = []
    p1.first_turn = False
    engine.active_player_id = "p1"

    actions_before = engine.get_available_mainstep_actions()
    support_before = {a["card_id"] for a in actions_before if a.get("action_type") == GameAction.MainStepPlaySupport}
    assert escape_a["game_card_id"] in support_before
    assert escape_b["game_card_id"] in support_before
    assert other_limited["game_card_id"] in support_before

    engine.current_decision = {
        "decision_type": DecisionType.DecisionMainStep,
        "decision_player": "p1",
        "available_actions": actions_before,
        "continuation": (lambda: None),
    }
    assert engine.handle_main_step_play_support("p1", {"card_id": escape_a["game_card_id"]})
    resolve_all_decisions(engine)

    assert not p1.used_limited_this_turn, "hSD12-015 should not consume the global LIMITED usage"

    actions_after = engine.get_available_mainstep_actions()
    support_after = {a["card_id"] for a in actions_after if a.get("action_type") == GameAction.MainStepPlaySupport}
    assert other_limited["game_card_id"] in support_after, "Other limited support should remain playable"
    assert escape_b["game_card_id"] not in support_after, "Same support name should be blocked for the rest of the turn"


def main():
    scenarios = [
        ("hBP07-004 on_move draw2", scenario_hbp07_004_draw2_on_own_move),
        ("hBP07-039 gift once/turn", scenario_hbp07_039_gift_once_per_turn),
        ("hBP03-033 tool conditional damage", scenario_hbp03_033_tool_damage_10_or_30),
        ("hBP07-042 art +50 after stage->deck", scenario_hbp07_042_second_art_bonus_on_stage_to_deck_this_turn),
        ("hBP07-004 cheer attach no instant lose", scenario_hbp07_004_cheer_step_attach_does_not_lose_game),
        ("hSD12-007 on-kill archive choose no crash", scenario_hsd12_007_on_kill_choose_archive_does_not_crash),
        ("hSD13-001 oshi archive->stage choose no crash", scenario_hsd13_001_oshi_choose_archive_stage_does_not_crash),
        ("internal error ends game neutral", scenario_internal_error_ends_game_neutral),
        ("hSD12-015 non-limited + same-name once/turn", scenario_hsd12_015_not_global_limited_but_once_per_turn_by_name),
    ]

    passed = 0
    for name, fn in scenarios:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")

    print(f"\\nResult: {passed}/{len(scenarios)} passed")
    return 0 if passed == len(scenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
