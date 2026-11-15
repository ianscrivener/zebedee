---
name: z-spike
description: Run a timeboxed spike (stage -1) to test feasibility or performance of an idea, record the results, and bring it to a decision. Use for experiments such as a new kernel, algorithm or library trial.
---

# z-spike — experiments

A spike's deliverable is **the verdict, not the code**. Probe code is throwaway.

1. **Get to stage -1.** Create the item (`--stage -1`) or advance an idea: `just z-item stage <id> --agent <uuid> --to -1`.
2. **Write the plan first:** `just z-item doc <id> spike --agent <uuid>`, then fill in Hypothesis, Success criterion and Timebox *before* writing code.
3. **Probe** on a branch named `spike/<short-name>`. Don't merge it.
4. **Measure** with the `z-run` skill. Use `--kind bench --mode controlled --item <id>`, and record a baseline run as well as the spike run.
5. **Write Results and a proposed Verdict** in `spike.md`: the numbers, briefly, with run IDs. One-line reason.
6. **Advance to 0:** `just z-item stage <id> --agent <uuid> --to 0`.
7. **Decide** if you were asked to; otherwise leave it at stage 0 for the user:

   ```
   just z-item decide <id> --agent <uuid> --verdict commit|reject|park --reason "<one line>" [--revisit "<trigger>"]
   ```

   Inconclusive → `park` with a revisit trigger (e.g. "retry when the harness measures memory").

Stop at the timebox even if the answer isn't clear. Inconclusive is a valid result.
