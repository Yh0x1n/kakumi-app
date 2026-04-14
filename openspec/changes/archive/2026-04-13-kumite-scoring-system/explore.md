# Exploration: Kumite Scoring System (WKF 2026) — Corrected Report

## Source
Official PDF: `docs/WKF 2026 Kumite Competition Rules MASTER COPY_V11.pdf`
Articles reviewed: 6.3, 7.7, 7.8, 8.1, 8.3, 8.5, 8.6, 8.10, 8.11, 10.2.1, 10.3, 10.6.1, 10.7.1, 12.2.1–12.2.4, 12.3.2

---

## ✅ Point Values — CONFIRMED (Art. 8.6)

| Technique | Points | Target | Article |
|-----------|--------|--------|---------|
| YUKO | 1 | TSUKI (straight punch) or UCHI (strike) to any scoring area | 8.6 |
| WAZA-ARI | 2 | CHUDAN kick (mid-body zone) | 8.6 |
| IPPON | 3 | JODAN kick (head) OR any valid technique on downed opponent* | 8.6 |

*Exception: HIZA GAMAE (one knee on ground while executing) does NOT count as downed.

---

## ❌ CRITICAL CORRECTIONS from Prior Exploration

### ERROR 1 — IPPON does NOT end the match immediately
**Wrong**: "IPPON = Immediate Victory"
**Correct (Art. 7.7)**: Match ends ONLY when lead >= 8 points. IPPON = 3 points, nothing more.

### ERROR 2 — "2 WAZA-ARI = Ippon" does NOT exist
**Wrong**: "2 Waza-ari = 1 Ippon. Match ends immediately."
**Correct**: Each score is independent. 2 WAZA-ARI = 4 points total. No conversion rule.

### ERROR 3 — YUKO was NOT eliminated
**Wrong**: "Yuko was eliminated in WKF 2026"
**Correct (Art. 8.6 + Art. 12.6 table)**: YUKO = 1 point, valid technique, fully active.

### ERROR 4 — Penalty escalation was wrong
**Wrong**: "5 CHUI = HANSOKU"
**Correct (Art. 10.2.1, 10.3)**: CHUI (max 3) → HANSOKU CHUI → HANSOKU. HANSOKU CHUI can also be direct for serious infractions.

---

## ✅ What Was Correct
- 6 scoring criteria (Art. 8.5): good form, sporting attitude, vigorous application, Zanshin, good timing, correct distance
- Score requires majority of judges (Art. 8.1): 2+ judges must signal
- HANSOKU does NOT give points to opponent — gives direct bout victory

---

## Match Termination Rules (Art. 7.7 + 12.2.1)

```
During match:
  lead >= 8 points → bout ends, leader wins

At time expiry:
  1. Higher total score → winner
  2. Tie + SENSHU (first unopposed score) → SENSHU holder wins
  3. Tie + no SENSHU + more IPPON → more IPPON wins (Art. 12.2.3a)
  4. Tie + equal IPPON + more WAZA-ARI → more WAZA-ARI wins (Art. 12.2.3b)
  5. All equal → HANTEI (judge vote, elimination) or HIKIWAKE (draw, round-robin)
```

---

## Round-Robin Special Rule (Art. 12.3.2)
When HANSOKU applied in round-robin bout:
- Opponent wins by 4-0 (counted as YUKO) OR by any score exceeding 4 points already obtained.
- Disqualified athlete score → set to 0.
- Athlete CAN continue competition after HANSOKU in round-robin.

---

## Implementation Implications
1. Track point differential for 8-pt lead termination
2. Track per-type counts (IPPON, WAZA_ARI, YUKO) for tiebreakers
3. Track SENSHU flag (boolean per athlete, revocable by operator)
4. Include YUKO as valid technique (1 point)
5. Differentiate HANSOKU behavior: elimination vs round-robin
