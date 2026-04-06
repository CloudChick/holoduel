#!/usr/bin/env python3
"""
hBP06-014 reduce_art_cost 턴 효과 작동 테스트

수정 내용: is_art_requirement_met에서 performance_performer_card를 임시 설정하여
on_art_cost_check 타이밍의 performer_is_specific_id 조건이 정상 평가되도록 함.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.card_database import CardDatabase
from app.gameengine import GameEngine


def create_test_engine():
    card_db = CardDatabase()
    deck_cards = {
        "hBP06-014": 1,
        "hBP06-010": 1,
        "hBP06-040": 48,
    }
    cheer_cards = {
        "hY01-001": 20,
    }
    player_infos = [
        {
            "player_id": "p1",
            "username": "TestPlayer1",
            "oshi_id": "hBP06-001",
            "deck": deck_cards,
            "cheer_deck": cheer_cards,
        },
        {
            "player_id": "p2",
            "username": "TestPlayer2",
            "oshi_id": "hBP06-001",
            "deck": deck_cards,
            "cheer_deck": cheer_cards,
        },
    ]
    return GameEngine(card_db, "test", player_infos)


def find_card_in_deck(player, card_id):
    for card in player.deck:
        if card["card_id"] == card_id:
            return card
    return None


def setup_player_stage(player, center_card_id, collab_card_id):
    center_card = find_card_in_deck(player, center_card_id)
    if center_card:
        player.deck.remove(center_card)
        player.center = [center_card]

    collab_card = find_card_in_deck(player, collab_card_id)
    if collab_card:
        player.deck.remove(collab_card)
        player.collab = [collab_card]


def attach_cheer(player, target_card):
    if player.cheer_deck:
        cheer = player.cheer_deck.pop(0)
        target_card["attached_cheer"].append(cheer)
        return cheer
    return None


def add_reduce_art_cost_turn_effect(player, target_game_card_id, source_card_id):
    turn_effect = {
        "timing": "on_art_cost_check",
        "effect_type": "reduce_art_cost",
        "color": "any",
        "amount": 1,
        "source_card_id": source_card_id,
        "conditions": [
            {
                "condition": "performer_is_specific_id",
                "required_id": target_game_card_id
            }
        ]
    }
    player.add_turn_effect(turn_effect)


def test_tc_a():
    """TC-A: #Art 콜라보 홀로멤에 reduce_art_cost가 적용되는지 확인"""
    print("=== TC-A: reduce_art_cost 적용 테스트 ===")

    engine = create_test_engine()
    p1 = engine.get_player("p1")

    setup_player_stage(p1, "hBP06-014", "hBP06-010")
    center = p1.center[0]
    collab = p1.collab[0]

    art = {
        "art_id": "test_art",
        "costs": [
            {"color": "white", "amount": 1},
            {"color": "any", "amount": 1}
        ],
        "power": 50
    }

    attach_cheer(p1, collab)

    result_before = p1.is_art_requirement_met(collab, art)
    if result_before:
        print("  FAIL: 턴 효과 없이도 아츠 요구조건이 충족됨 (예상: 미충족)")
        return False
    print("  OK: 턴 효과 없이 아츠 요구조건 미충족 확인")

    add_reduce_art_cost_turn_effect(p1, collab["game_card_id"], center["game_card_id"])

    result_after = p1.is_art_requirement_met(collab, art)
    if not result_after:
        print("  FAIL: reduce_art_cost 턴 효과 적용 후에도 아츠 요구조건 미충족")
        return False
    print("  OK: reduce_art_cost 적용 후 아츠 요구조건 충족 확인")

    return True


def test_tc_b():
    """TC-B: 코스트 감소 후 실제 감소된 코스트로 아츠 사용 가능한지 확인"""
    print("\n=== TC-B: 감소된 코스트 사용 가능 테스트 ===")

    engine = create_test_engine()
    p1 = engine.get_player("p1")

    setup_player_stage(p1, "hBP06-014", "hBP06-010")
    center = p1.center[0]
    collab = p1.collab[0]

    expensive_art = {
        "art_id": "expensive_test",
        "costs": [
            {"color": "white", "amount": 2},
            {"color": "any", "amount": 1}
        ],
        "power": 100
    }

    attach_cheer(p1, collab)
    attach_cheer(p1, collab)

    result_no_effect = p1.is_art_requirement_met(collab, expensive_art)
    if result_no_effect:
        print("  FAIL: 감소 없이 코스트 충족됨 (예상: 미충족)")
        return False
    print("  OK: 감소 없이 코스트 미충족 확인 (필요: white2+any1, 보유: white2)")

    add_reduce_art_cost_turn_effect(p1, collab["game_card_id"], center["game_card_id"])

    result_with_effect = p1.is_art_requirement_met(collab, expensive_art)
    if not result_with_effect:
        print("  FAIL: 감소 후에도 코스트 미충족")
        return False
    print("  OK: 감소 후 코스트 충족 확인 (any:1 감소, 실효 코스트: white2)")

    return True


def test_tc_c():
    """TC-C: #Art 태그 없는 콜라보에는 코스트 감소 미적용 확인"""
    print("\n=== TC-C: #Art 태그 없는 홀로멤 미적용 테스트 ===")

    engine = create_test_engine()
    p1 = engine.get_player("p1")

    setup_player_stage(p1, "hBP06-014", "hBP06-040")
    center = p1.center[0]
    collab = p1.collab[0]

    if "#Art" in collab.get("tags", []):
        print("  FAIL: 콜라보 홀로멤에 #Art 태그가 있음 (테스트 설정 오류)")
        return False
    print(f"  OK: 콜라보 홀로멤 태그 확인: {collab.get('tags', [])}")

    art = {
        "art_id": "test_art",
        "costs": [
            {"color": "white", "amount": 1},
            {"color": "any", "amount": 1}
        ],
        "power": 50
    }

    attach_cheer(p1, collab)

    # performer_is_specific_id 조건에 다른 카드 ID를 지정하여 매칭 실패 시뮬레이션
    add_reduce_art_cost_turn_effect(p1, "nonexistent_card_id", center["game_card_id"])

    result = p1.is_art_requirement_met(collab, art)
    if result:
        print("  FAIL: 다른 카드 대상 턴 효과가 이 홀로멤에 적용됨")
        return False
    print("  OK: 다른 카드 대상 턴 효과 미적용 확인")

    return True


def main():
    print("hBP06-014 reduce_art_cost 턴 효과 작동 테스트")
    print("수정: is_art_requirement_met에서 performance_performer_card 임시 설정\n")

    results = []
    results.append(test_tc_a())
    results.append(test_tc_b())
    results.append(test_tc_c())

    print("\n=== 테스트 결과 요약 ===")
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"PASS: 모든 테스트가 통과했습니다! ({passed}/{total})")
    else:
        print(f"FAIL: 일부 테스트가 실패했습니다. ({passed}/{total})")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
