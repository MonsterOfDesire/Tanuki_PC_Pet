# Mood climate calibration

The runtime keeps the existing mood bands (`normal >= 50`, `low >= 20`,
`severe < 20`). Climate profiles control only tick frequency, direction and
magnitude; they do not pull scores toward a target value.

## Reproduce the simulation

From the `tanuki_app` directory:

```powershell
python tools/calibrate_mood.py --runs 2000 --seed-offset 0
python tools/calibrate_mood.py --runs 10000 --seed-offset 900000001 `
  --scenario balanced_child_household
```

One simulated minute contains 20 mood ticks, matching the runtime's
three-simulated-second timer. Household scenarios import the real Sleep and
Chorus timing rules: initial waits, selected frequency policy, phase
occupation, cooldowns, mutually exclusive Activity ownership, natural-mood
pauses and capped maintenance rewards. They assume the child remains in a
five-pet cluster, so nearby-company and adult-comfort protection are present
throughout. This is a deterministic worst-case statistical guard for mood
protection, not a replacement for graphical 1x/8x smoke testing.

## 2026-08-21 balanced profile result

The 2,000-run suite used seeds not involved in parameter selection. Each run
covered three simulated hours.

| Scenario | Normal | Low | Severe | First low | First severe |
|---|---:|---:|---:|---:|---:|
| Child, five-pet life, frequent Chorus | 95.20% | 4.80% | 0.00% | 48.45 min | — |
| Child, five-pet life, normal Chorus | 73.08% | 26.92% | 0.00% | 15.00 min | — |
| Child near an adult, no Activities | 18.64% | 81.36% | 0.00% | 5.10 min | 77.05 min* |
| Child alone | 2.24% | 16.04% | 81.72% | 3.70 min | 31.15 min |
| Adult, five-pet life with normal Chorus | 75.59% | 24.41% | 0.00% | 19.38 min | — |
| Cheerful child, five-pet life | 100.00% | 0.00% | 0.00% | — | — |
| Expressive child alone | 0.25% | 0.73% | 99.02% | 0.50 min | 1.80 min |

The frequent-Chorus stress scenario spent 66.59% of ticks inside Sleep or
Chorus. Completion rewards retain their nominal `+3 / +2 / +1` values, but
Sleep can only maintain mood up to 55 and Chorus up to 60; neither can stack a
healthy character toward 100. The held-out 10,000-run check returned
`95.20% normal / 4.80% low / 0.00% severe`; 58.84% of individual child runs
entered low within the first hour, with a median first-low time of 48.55
minutes. Treating two child trajectories as independent gives an 83.06%
chance that at least one enters low during the hour. The normal-frequency
scenario spends 26.92% of its time in low, so the frequency control still has
a meaningful protective effect without making low impossible.

`*` The near-adult/no-Activity severe occupancy rounds to 0.00%; the median is
calculated only from the very small subset of runs that eventually reached it.

Balanced therefore uses a stronger downward drift while a child is normal to
offset the real Sleep/Chorus pause and reward cadence. Activity rewards are
maintenance effects rather than uncapped positive drift. Low-band children gain
natural resilience; a nearby adult supplies the full bias while an isolated
child receives only 75%, allowing prolonged separation to reach severe in
about half an hour rather than immediately. Adults use smaller negative
changes plus band-aware self-regulation. No profile pulls a score toward a
hidden target.
