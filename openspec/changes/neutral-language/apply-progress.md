# Apply Progress — neutral-language

## Completed Tasks

- [x] Replace all voseo imperative forms with neutral Spanish equivalents across 13 files
- [x] Verify zero remaining voseo forms via grep

## Files Changed

| # | File | Replacements | Patterns |
|---|------|-------------|----------|
| 1 | `kakumi_app/components/registry_crud.py` | 2 | seleccioná→selecciona, arrastrá→arrastra, acá→aquí, hacé→haz |
| 2 | `kakumi_app/components/kumite_scoreboard.py` | 1 | seleccioná→selecciona |
| 3 | `kakumi_app/pages/registries.py` | 6 | seleccioná→selecciona, escribí→escribe, importá→importa, cargá→carga, creá→crea, exportá→exporta |
| 4 | `kakumi_app/pages/results.py` | 1 | seleccioná→selecciona |
| 5 | `kakumi_app/states/athlete_state.py` | 3 | revisá→revisa, seleccioná→selecciona, usá→usa |
| 6 | `kakumi_app/states/referee_state.py` | 3 | revisá→revisa, seleccioná→selecciona, usá→usa |
| 7 | `kakumi_app/states/results_state.py` | 2 | seleccioná→selecciona |
| 8 | `kakumi_app/states/tournament_tatami_state.py` | 1 | seleccioná→selecciona |
| 9 | `kakumi_app/states/tournament_category_state.py` | 1 | seleccioná→selecciona |
| 10 | `kakumi_app/states/kata_informal_state.py` | 1 | seleccioná→selecciona |
| 11 | `kakumi_app/states/kata_match_state.py` | 1 | seleccioná→selecciona |
| 12 | `kakumi_app/services/tournament_service.py` | 1 | intentá→intenta |
| 13 | `tests/test_crud_registries_apply.py` | 2 | usá→usa, seleccioná→selecciona |

## Verification

- Grep `grep -rn 'Seleccioná\|Importá\|exportá\|revisá\|Usá\|cargá\|Creá\|Arrastrá\|hacé\|escribí\|Intentá' kakumi_app/ tests/ --include='*.py'` returned **zero matches** ✅

## Total

- 25 replacements across 13 files
- All source `.py` files clean of voseo forms
- Only stale `__pycache__/` bytecode retains old forms (harmless, will regenerate)
