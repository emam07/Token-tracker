---
name: Suggest a new rule
about: Propose a new pre-flight rule for the analyzer
title: "[RULE] "
labels: new-rule
---

## Pattern this rule should catch

<!-- One sentence: what wasteful pattern does this detect? -->

## Example prompts that should trigger it

```
<paste 1-3 example prompts>
```

## Example prompts that should NOT trigger it (false-positive guards)

```
<paste 1-3 prompts that look similar but are fine>
```

## Suggested severity

- [ ] high   (clear waste, real cost)
- [ ] medium (suboptimal, costs more output)
- [ ] low    (cosmetic, costs a few tokens)

## Suggested fix message

<!-- What would you tell the user? -->
