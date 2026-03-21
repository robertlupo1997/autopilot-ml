---
phase: 23
status: passed
score: 4/4
---

# Phase 23 Verification: Add Missing CLI Flags

## Success Criteria

1. [x] `--model-name` argparse argument added to CLI, passed through to `plugin_settings["model_name"]` for FT domain
   - Added at cli.py:102-104, wired at cli.py:155-156
2. [x] `--direction` argparse argument added to CLI (choices: minimize, maximize), overrides auto-detected direction in config
   - Added at cli.py:105-108, wired at cli.py:150-151
3. [x] `mlforge dataset goal --domain finetuning --model-name meta-llama/Llama-3.2-1B` works without argparse error
   - Test: TestModelNameFlag.test_model_name_flag
4. [x] `mlforge dataset goal --metric rmse --direction minimize` correctly sets direction=minimize
   - Test: TestDirectionFlag.test_direction_minimize

## Tests Added
- TestModelNameFlag: 2 tests (flag accepted + default absent)
- TestDirectionFlag: 4 tests (minimize, maximize, default, invalid rejected)

## Integration Gaps Closed
- INT-FT-MODEL-NAME: `--model-name` CLI flag now accepted
- INT-DIRECTION-FLAG: `--direction` CLI flag now overrides auto-detected direction
