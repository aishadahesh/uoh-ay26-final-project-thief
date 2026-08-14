# Thief replay evidence

This directory contains the two representative examples used by the root academic report. Each animation is stored beside the signed source log from which it was generated. The copies are immutable documentation evidence; active match output remains under `results/` and is not committed as part of this documentation change.

| Example | Role outcome | Signed source | Rendered view |
|---|---|---|---|
| G009 sub-game 2 | Thief win by survival after 35 steps | `thief-win-G009-g02.json` | `thief-win-G009-g02.gif` |
| G009 sub-game 6 | Thief loss by capture after 25 steps | `thief-loss-G009-g06.json` | `thief-loss-G009-g06.gif` |

The renderer is maintained once in the sibling Cop repository. From this Thief repository root, regenerate either animation with the Cop project's environment and script:

```powershell
uv run --project ..\uoh-ay26-final-project-cop python `
  ..\uoh-ay26-final-project-cop\scripts\visualize_game_log.py `
  --input assets/replays/thief-win-G009-g02.json `
  --output assets/replays/thief-win-G009-g02.gif

uv run --project ..\uoh-ay26-final-project-cop python `
  ..\uoh-ay26-final-project-cop\scripts\visualize_game_log.py `
  --input assets/replays/thief-loss-G009-g06.json `
  --output assets/replays/thief-loss-G009-g06.gif
```

The JSON is authoritative. The GIF is a reviewer-friendly visualization produced by the same replay parser and commitment checks.
