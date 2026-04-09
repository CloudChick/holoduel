#!/usr/bin/env python3
"""
hSD09-007 카드 구현 테스트
- 카드 로드 및 구조 검증
- gift_effects 조건: this_card_is_collab, opponent_turn, my_life_less_than_opponent
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.card_database import CardDatabase
from app.gameengine import GameEngine, Condition


def test_card_load():
    """hSD09-007 카드가 정상 로드되고 구조가 올바른지 검증"""
    print("=== hSD09-007 카드 로드 테스트 ===")

    card_db = CardDatabase()
    card = card_db.get_card_by_id("hSD09-007")
    if not card:
        print("FAIL: hSD09-007 not found in card database")
        return False

    checks = [
        (card["card_type"] == "holomem_debut", f"card_type: expected holomem_debut, got {card['card_type']}"),
        ("shiranui_flare" in card["card_names"], f"card_names missing shiranui_flare: {card['card_names']}"),
        (card["rarity"] == "c", f"rarity: expected c, got {card['rarity']}"),
        (card["colors"] == ["yellow"], f"colors: expected ['yellow'], got {card['colors']}"),
        (card["hp"] == 100, f"hp: expected 100, got {card['hp']}"),
        (card["baton_cost"] == 1, f"baton_cost: expected 1, got {card['baton_cost']}"),
        ("#Summer" in card["tags"], f"tags missing #Summer: {card['tags']}"),
    ]

    arts = card.get("arts", [])
    checks.append((len(arts) == 1, f"arts count: expected 1, got {len(arts)}"))
    if arts:
        checks.append((arts[0]["art_id"] == "cold_one_long_wait", f"art_id: expected cold_one_long_wait, got {arts[0]['art_id']}"))
        checks.append((arts[0]["power"] == 80, f"art power: expected 80, got {arts[0]['power']}"))

    gift = card.get("gift_effects", [])
    checks.append((len(gift) == 1, f"gift_effects count: expected 1, got {len(gift)}"))
    if gift:
        g = gift[0]
        checks.append((g["timing"] == "on_down", f"gift timing: expected on_down, got {g['timing']}"))
        checks.append((g["effect_type"] == "modify_next_life_loss", f"gift effect_type: expected modify_next_life_loss, got {g['effect_type']}"))
        checks.append((g["amount"] == -1, f"gift amount: expected -1, got {g['amount']}"))

        conds = g.get("conditions", [])
        checks.append((len(conds) == 3, f"conditions count: expected 3, got {len(conds)}"))
        cond_names = [c["condition"] for c in conds]
        checks.append(("this_card_is_collab" in cond_names, f"missing this_card_is_collab in {cond_names}"))
        checks.append(("opponent_turn" in cond_names, f"missing opponent_turn in {cond_names}"))
        checks.append(("my_life_less_than_opponent" in cond_names, f"missing my_life_less_than_opponent in {cond_names}"))

    all_ok = True
    for ok, msg in checks:
        if not ok:
            print(f"  FAIL: {msg}")
            all_ok = False

    if all_ok:
        print("  PASS: card structure OK")
    return all_ok


def main():
    print("hSD09-007 (shiranui_flare debut / gift: modify_next_life_loss) test\n")
    results = [test_card_load()]

    print(f"\n=== Result: {sum(results)}/{len(results)} passed ===")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
