#!/usr/bin/env python3
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
    engine.random_gen = random.Random(0)
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


def scenario_stage_leave_promotes_top_stacked_holomem():
    from_zones = ["center", "backstage", "collab"]
    to_zones = ["deck", "hand", "holopower", "archive"]

    for from_zone in from_zones:
        for to_zone in to_zones:
            engine = make_custom_engine(
                p1_deck={
                    "hSD12-003": 1,
                    "hSD12-004": 1,
                    "hSD12-007": 1,
                    "hBP01-114": 1,
                },
                p2_deck={
                    "hBP07-036": 1,
                },
                oshi_p1="hSD12-001",
                oshi_p2="hBP01-001",
            )
            p1 = engine.get_player("p1")

            top = take_card(p1, "hSD12-007")
            stacked_top = take_card(p1, "hSD12-004")
            stacked_other = take_card(p1, "hSD12-003")
            attached_support = take_card(p1, "hBP01-114")
            attached_cheer = take_cheer(p1, "hY03-001")

            top["stacked_cards"] = [stacked_top, stacked_other]
            top["attached_support"] = [attached_support]
            top["attached_cheer"] = [attached_cheer]

            p1.center = []
            p1.backstage = []
            p1.collab = []
            if from_zone == "center":
                p1.center = [top]
            elif from_zone == "backstage":
                p1.backstage = [top]
            else:
                p1.collab = [top]

            assert p1.move_card(top["game_card_id"], to_zone), f"move_card failed for {from_zone}->{to_zone}"

            zone_map = {
                "deck": p1.deck,
                "hand": p1.hand,
                "holopower": p1.holopower,
                "archive": p1.archive,
            }
            destination_ids = {card["game_card_id"] for card in zone_map[to_zone]}
            archive_ids = {card["game_card_id"] for card in p1.archive}

            assert stacked_top["game_card_id"] in destination_ids, f"Top stacked holomem must move to {to_zone} ({from_zone})"
            assert top["game_card_id"] in archive_ids, f"Original stage holomem must be archived ({from_zone}->{to_zone})"
            assert stacked_other["game_card_id"] in archive_ids, f"Other stacked card must be archived ({from_zone}->{to_zone})"
            assert attached_support["game_card_id"] in archive_ids, f"Attached support must be archived ({from_zone}->{to_zone})"
            assert attached_cheer["game_card_id"] in archive_ids, f"Attached cheer must be archived ({from_zone}->{to_zone})"

            stage_ids = {card["game_card_id"] for card in p1.get_holomem_on_stage()}
            assert top["game_card_id"] not in stage_ids
            assert stacked_top["game_card_id"] not in stage_ids

            move_events = [e for e in engine.all_events if e.get("event_type") == EventType.EventType_MoveCard]
            assert move_events, f"Expected move event for {from_zone}->{to_zone}"
            assert move_events[-1].get("card_id") == stacked_top["game_card_id"], f"Move event should reference promoted holomem ({from_zone}->{to_zone})"


def scenario_hsd12_016_geow_can_choose_non_top_cheer_from_cheer_deck():
    engine = make_custom_engine(
        p1_deck={
            "hSD12-011": 1,
            "hSD12-016": 1,
        },
        p2_deck={
            "hBP07-036": 1,
        },
        oshi_p1="hSD12-001",
        oshi_p2="hBP01-001",
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")

    bijou = take_card(p1, "hSD12-011")
    geow = take_card(p1, "hSD12-016")
    p1.center = [bijou]
    p2.center = [take_card(p2, "hBP07-036")]

    # on_attach choice의 비용(옐 1장 아카이브)을 위해 스테이지에 옐 1장을 둔다.
    bijou["attached_cheer"] = [take_cheer(p1, "hY03-001")]

    # 비공개 처리 없이 특정 옐을 고를 수 있는지 검증하기 위해 순서를 고정한다.
    cheer_top = take_cheer(p1, "hY02-001")
    cheer_pick = take_cheer(p1, "hY05-001")
    cheer_extra = take_cheer(p1, "hY06-001")
    p1.cheer_deck = [cheer_top, cheer_pick, cheer_extra]

    p1.hand = [geow]
    p1.first_turn = False
    p2.first_turn = False
    engine.active_player_id = "p1"

    actions = engine.get_available_mainstep_actions()
    engine.current_decision = {
        "decision_type": DecisionType.DecisionMainStep,
        "decision_player": "p1",
        "available_actions": actions,
        "continuation": (lambda: None),
    }

    assert engine.handle_main_step_play_support("p1", {"card_id": geow["game_card_id"]})
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionEffect_ChooseCardsForEffect

    # GEOW 부착 대상(비쥬) 선택
    engine.handle_game_message(
        "p1",
        GameAction.EffectResolution_ChooseCardsForEffect,
        {"card_ids": [bijou["game_card_id"]]},
    )
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionChoice

    # on_attach 능력 사용(패스하지 않음)
    engine.handle_game_message(
        "p1",
        GameAction.EffectResolution_MakeChoice,
        {"choice_index": 0},
    )

    # 수정 전에는 send_cheer라서 이 단계가 없고 top 카드가 자동 처리됐다.
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionEffect_ChooseCardsForEffect
    assert engine.current_decision.get("from_zone") == "cheer_deck"
    can_choose = set(engine.current_decision.get("cards_can_choose", []))
    assert cheer_top["game_card_id"] in can_choose
    assert cheer_pick["game_card_id"] in can_choose

    # top이 아닌 카드 선택
    engine.handle_game_message(
        "p1",
        GameAction.EffectResolution_ChooseCardsForEffect,
        {"card_ids": [cheer_pick["game_card_id"]]},
    )
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionEffect_ChooseCardsForEffect

    # 옐 부착 대상(비쥬) 선택
    engine.handle_game_message(
        "p1",
        GameAction.EffectResolution_ChooseCardsForEffect,
        {"card_ids": [bijou["game_card_id"]]},
    )

    attached_ids = {c["game_card_id"] for c in bijou.get("attached_cheer", [])}
    cheer_deck_ids = {c["game_card_id"] for c in p1.cheer_deck}
    assert cheer_pick["game_card_id"] in attached_ids, "선택한(비 top) 옐이 부착되어야 한다"
    assert cheer_pick["game_card_id"] not in cheer_deck_ids, "선택한 옐은 옐 덱에서 빠져야 한다"
    assert cheer_top["game_card_id"] in cheer_deck_ids, "선택하지 않은 top 옐은 옐 덱에 남아야 한다"
    assert not engine.is_game_over(), "GEOW 처리 중 내부 오류로 게임이 종료되면 안 된다"


def scenario_hsd12_011_bloom_buff_only_selected_holomem():
    engine = make_custom_engine(
        p1_deck={
            "hSD12-011": 1,
            "hSD12-010": 1,
        },
        p2_deck={
            "hBP07-036": 1,
        },
        oshi_p1="hSD12-001",
        oshi_p2="hBP01-001",
    )
    p1 = engine.get_player("p1")
    p2 = engine.get_player("p2")

    bijou_second = take_card(p1, "hSD12-011")
    bijou_first = take_card(p1, "hSD12-010")
    target = take_card(p2, "hBP07-036")

    p1.center = [bijou_second]
    p1.backstage = [bijou_first]
    p2.center = [target]
    engine.active_player_id = "p1"

    # 블룸 효과의 "옐 1장 아카이브" 비용을 위해 옐을 붙인다.
    bijou_second["attached_cheer"].append(take_cheer(p1, "hY03-001"))
    bijou_first["attached_cheer"].append(take_cheer(p1, "hY03-001"))

    bloom_choice = deepcopy(bijou_second["bloom_effects"][1])
    add_ids_to_effects([bloom_choice], "p1", bijou_second["game_card_id"])
    engine.begin_resolving_effects([bloom_choice], engine.blank_continuation)

    # choice: archive_cheer_from_holomem 선택
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionChoice
    engine.handle_game_message("p1", GameAction.EffectResolution_MakeChoice, {"choice_index": 0})

    # archive할 옐 선택 (1장)
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionEffect_ChooseCardsForEffect
    cheer_to_archive = engine.current_decision["cards_can_choose"][0]
    engine.handle_game_message("p1", GameAction.EffectResolution_ChooseCardsForEffect, {"card_ids": [cheer_to_archive]})

    # +40 대상은 bijou_second로 지정
    assert engine.current_decision and engine.current_decision["decision_type"] == DecisionType.DecisionEffect_ChooseCardsForEffect
    engine.handle_game_message(
        "p1",
        GameAction.EffectResolution_ChooseCardsForEffect,
        {"card_ids": [bijou_second["game_card_id"]]},
    )

    assert p1.turn_effects, "턴 효과가 추가되어야 한다"
    power_boost_effect = p1.turn_effects[-1]
    conds = power_boost_effect.get("conditions", [])
    assert any(
        c.get("condition") == "performer_is_specific_id" and c.get("required_id") == bijou_second["game_card_id"]
        for c in conds
    ), "선택한 홀로멤만 대상으로 하는 performer_is_specific_id 조건이 있어야 한다"

    # 선택하지 않은 홀로멤(1st 비쥬)으로 아츠 수행 시 +40이 적용되면 안 된다.
    target["damage"] = 0
    engine.begin_perform_art(
        bijou_first["game_card_id"],
        "permeating_light",
        target["game_card_id"],
        engine.blank_continuation,
    )
    resolve_all_decisions(engine)
    assert target["damage"] == 30, f"선택되지 않은 홀로멤 아츠는 +40이 붙으면 안 됨 (actual={target['damage']})"


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
        ("stage leave promotes top stacked holomem", scenario_stage_leave_promotes_top_stacked_holomem),
        ("hSD12-016 GEOW choose cheer from deck", scenario_hsd12_016_geow_can_choose_non_top_cheer_from_cheer_deck),
        ("hSD12-011 bloom buff selected target only", scenario_hsd12_011_bloom_buff_only_selected_holomem),
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
