# Indicator catalog (data/indicators.json)

**All numeric values in this file are PLACEHOLDERS, not clinical values.**
They exist so the simulator and the data layer can be built and tested. Before
any value is used for real guidance, it must be replaced with a sourced limit
and verified (see AGENTS.md hard rules 4 and 6).

## Fields

| field | meaning |
|---|---|
| key | Stable identifier used in `Reading.indicator_key` and in code |
| label | Name shown to the user |
| unit | Display unit |
| bad_direction | `high` or `low`: the direction that counts as unfavorable |
| body_region | Body map region the indicator is shown on |
| input_type | `device` or `self-report` |
| min_valid | Lowest value accepted as valid input (placeholder) |
| max_valid | Highest value accepted as valid input (placeholder) |
| mad_floor | Minimum MAD used in the robust z-score so a flat history never divides by zero (placeholder) |
| normal_center | Centre of the simulated "normal" values. Simulator only (placeholder) |
| normal_wobble | Standard deviation of day-to-day noise in the simulator. Simulator only (placeholder) |

## Current entries

| key | label | unit | bad direction | region | input |
|---|---|---|---|---|---|
| resting_hr | Resting heart rate | bpm | high | chest | device |
| sleep_hours | Sleep | hours | low | head | self-report |
| temperature | Body temperature | °C | high | torso | device |
| mood | Mood and stress | 1 to 5 | low | head | self-report |
| exercise_min | Exercise | minutes | low | legs | self-report |
| spo2 | Blood oxygen | % | low | lungs | device |

The `min_valid`, `max_valid`, `mad_floor`, `normal_center` and `normal_wobble`
values are the only numbers in the file. None of them is a clinical limit.
