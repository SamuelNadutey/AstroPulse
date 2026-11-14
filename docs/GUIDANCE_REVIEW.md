# Guidance safety review (data/guidance.json)

Status: **PENDING human safety-owner sign-off.** No guidance wording has been
changed by this review. The findings below are recommendations for the person
who owns the safety wording to accept, reject or rewrite.

Reviews performed:
1. Agent self-review of every line of `data/guidance.json` (this file).
2. Independent second review by a separate reviewer agent, read-only, against
   `data/sources.json`. This is an AI reviewer, not a clinician, and does not
   replace the human sign-off.

Categories: DIAG = diagnosis-like wording; UNSAFE = advice that could delay
care or be unsafe; SOURCE = claim not supported by listed source; CONTACT =
missing or weak contact-ground statement; WORDING = plain-language or tone
issue.

## Cross-cutting findings (all rules)

- **TODO sources (high):** all 48 suggested actions use `source_ids: ["TODO"]`.
  AGENTS.md rule 4 requires a source on every action prompt. Until sourced,
  these actions must not be shown as sourced guidance.
- **Unverified sources (high):** all 14 entries in `data/sources.json` are
  `verified: false`. See PROGRESS.md "Needs human verification".
- **No on-board emergency direction in red rules (high):** no red rule says
  what to do immediately for danger signs (for example chest pain, fainting,
  confusion, severe breathlessness, heat illness, or any thought of self-harm).
  Blackout paths say only "log it" or "add it to the relay summary". This can
  delay care. Needs a source and a human decision (for example a link to crew
  emergency procedures).
- **Red rules cite `src_nasa_std_3001_v1` for "contact ground now" (medium):**
  that source's supports text covers fitness for duty, exposure limits and
  countermeasures. It does not support the contact timing.
- **Numbers in `remeasure_after` (low):** AGENTS.md allows numbers only in
  spo2 text and remeasure_after. Confirm the card displays them as intended.
- **Vague timeframes (low):** "a couple of nights", "several days", "soon",
  "or you feel unwell" have no source and no named symptoms.
- **Jargon (low):** "Circadian disruption", "countermeasure", "cardiovascular
  recovery", "sleep countermeasures".

## Per-rule findings

### resting_hr.yellow
- DIAG: "Caffeine or mild dehydration" names a cause without evidence.
- SOURCE: contributors "Caffeine or mild dehydration" and "Stress from workload"
  are not supported by `src_arzeno_cv`.
- WORDING: "stimulant use" reads like a substance-use prompt.
- CONTACT: "or you feel unwell" names no symptoms.

### resting_hr.orange
- DIAG: "Dehydration or illness starting" names an illness.
- SOURCE: `src_otsuka_hrv` is about heart rate variability, not resting heart
  rate (its own supports text says so). Weak support.
- SOURCE: "Reduced cardiovascular recovery" is not supported.
- CONTACT: "or other symptoms appear" names no symptoms.

### resting_hr.red
- DIAG: "Significant cardiovascular stress", "Dehydration or illness".
- UNSAFE: "Stop strenuous activity and sit quietly" is the only immediate step.
  No emergency direction for chest pain, fainting or breathlessness.
- CONTACT: blackout path is only "log it and add it to the relay summary".
- SOURCE: `src_nasa_std_3001_v1` does not support "contact now".

### resting_hr.drift
- DIAG: "Gradual deconditioning" names a condition.
- SOURCE: only `src_otsuka_hrv` (HRV, not resting HR). Trend claim weak.

### sleep_hours.yellow
- SOURCE: "Keep the sleep area dark and quiet" is not in `src_nasa_sleep_evidence`.
- SOURCE: contributors "Shift schedule", "Noise or light" are not supported.
- CONTACT: "more than a couple of nights" is unsourced.

### sleep_hours.orange
- SOURCE: "low enough to affect alertness": neither source names alertness.
- SOURCE: "Ask about adjusting the light schedule" is not in a listed source.
- WORDING: "Circadian disruption", "sleep countermeasures" are jargon.

### sleep_hours.red
- WORDING: "may affect performance and health" implies a health outcome.
- SOURCE: `src_nasa_std_3001_v1` does not support "contact now".
- CONTACT: "now" may be stronger than the evidence; for the owner to decide
  whether this should be "soon".

### sleep_hours.drift
- SOURCE: `src_hera_2020` studies cognition under sleep restriction in 32
  subjects. It does not support a trend in sleep duration. Its verify_note says
  the author list is garbled.

### temperature.yellow
- DIAG: "Minor infection" names an infection.
- SOURCE: `src_stahn_temp_2017` does not support "warm environment" or "infection".
- UNSAFE: "Rest and rehydrate" is a treatment-type instruction, unsourced (TODO).
- CONTACT: "or you feel unwell" names no symptoms.

### temperature.orange
- DIAG: "Infection or inflammation" names conditions.
- SOURCE: `src_stahn_temp_2017` does not support infection, inflammation or
  "equipment error".
- UNSAFE: "Move to a cooler area if possible" has no warning signs.
- CONTACT: "soon" with no symptom list may be too slow.

### temperature.red
- DIAG: "Significant infection or heat stress".
- UNSAFE: "Stop exertion and cool down if possible" has no emergency direction
  (confusion, fainting, inability to drink, seizure).
- UNSAFE: "Verify the sensor is attached correctly" is the second action with a
  15-minute remeasure. A sensor check could delay care if the reading is real.
- CONTACT: blackout path is only "log it".
- SOURCE: `src_nasa_std_3001_v1` does not support "contact now".

### temperature.drift
- DIAG: "Developing illness" names a condition.
- SOURCE: `src_stahn_temp_2017` does not support "gradual overheating",
  "developing illness" or "sensor calibration shift".
- WORDING: "Gradual overheating" is condition-like.

### mood.yellow
- SOURCE: `src_nasa_behav_evidence` does not support the specific contributors
  or "talk with a crewmate".
- CONTACT: no safety wording. Consider telling the person to tell ground or a
  crewmate if they feel unsafe.

### mood.orange
- SOURCE (high): "mindfulness or exercise block" as a countermeasure is
  contradicted by `src_nasa_behav_risk_page`, which says validated countermeasures
  for exploration missions are not yet available. "Mindfulness" has no source.
- SOURCE: `src_hera_2020` (cognition under sleep restriction) is cited for mood.
  It is not about mood.
- CONTACT: "Contact ground soon" with no safety escalation for low mood.
- WORDING: "countermeasure" is jargon.

### mood.red
- DIAG (high): "Burnout" and "Sleep or health problem" are condition labels.
- UNSAFE (high): no crisis or safety direction for very low mood. Nothing says to
  tell a crewmate or ground immediately, or to follow emergency procedures if
  the person feels at risk. This needs a human-written, sourced crisis pathway.
- UNSAFE: "Ask a crewmate to stay nearby" is unsourced (TODO).
- SOURCE: "Pause non-essential demands" is unsourced. The cited risk page says
  countermeasures are not validated, which the red actions do not reflect.
- CONTACT: blackout path is only "log it for the relay summary".
- SOURCE: `src_nasa_std_3001_v1` does not support "contact now".

### mood.drift
- SOURCE: `src_nasa_behav_evidence_update` supports isolation and distance risk.
  It does not support "Declining sleep" or "Increasing workload" as contributors,
  nor the trend claim.
- SOURCE: "Plan a social or leisure activity" is unsourced.

### exercise_min.yellow
- SOURCE: "below target" implies a target. No listed source gives a daily target.
  `src_nasa_exercise_iws` gives a capacity loss figure after long missions,
  not a target. Also check that no target is implied by the app's data.
- CONTACT: "for several days" is an unsourced threshold.

### exercise_min.orange
- SOURCE: `src_loerch_exercise` does not support "Prioritize the next scheduled
  exercise session" or "Discuss alternative exercises with ground". Its URL was
  built from the DOI and its authors are unconfirmed.
- WORDING: "Low energy or mood" as a contributor can hint at a condition.

### exercise_min.red
- DIAG: "Illness or injury" names conditions.
- UNSAFE: "Assess whether equipment or health is blocking exercise" asks the
  person to self-assess health and could delay care for an injury.
- SOURCE: `src_nasa_exercise_iws` does not support "far below target" as a
  severity level. `src_nasa_std_3001_v1` does not support "contact now".
- CONTACT: blackout path is only "log it".

### exercise_min.drift
- SOURCE: `src_roberts_2025` supports muscle loss and exercise as a
  countermeasure. It does not support a downward trend in self-reported minutes
  or "Reduced motivation".

### spo2.yellow
- DIAG: "Mild breathing issue" names a condition.
- UNSAFE (high): "Contact ground if the reading stays low or you feel short of
  breath" makes breathlessness conditional. It should trigger immediate action
  and probably escalate to red/emergency procedures.
- SOURCE: `src_statpearls_pulseox` supports the normal range and the 90 percent
  hypoxemia cut-off. It does not support the yellow band or "breathing issue".
- UNSAFE/TODO: "Rest quietly and recheck" is unsourced.

### spo2.orange
- DIAG: "Breathing issue", "Reduced lung function" name conditions. "Reduced
  lung function" is not supported by the source.
- UNSAFE (high): "Rest and breathe slowly" is a breathing instruction presented
  as treatment, unsourced, with no warning signs or emergency direction.
- CONTACT: "soon" with no symptom list may be too slow for low oxygen.
- UNSAFE: 10-minute remeasure could delay care if the reading is real.

### spo2.red
- DIAG: "Severe breathing problem" names a condition.
- UNSAFE (high): "Recheck with the sensor at rest" with a 5-minute remeasure is
  the first step, ahead of emergency action. A repeat check could delay response.
- UNSAFE (high): no direction for breathlessness, confusion, chest pain or
  inability to speak.
- WORDING: "immediately if the link is available" conflicts with contact text
  "now, or as soon as the communications link allows". Make them consistent.
- CONTACT: blackout path is only "log it".
- SOURCE: `src_nasa_std_3001_v1` does not support "contact now".

### spo2.drift
- DIAG: "Developing breathing issue" names a condition.
- SOURCE: `src_statpearls_pulseox` does not support a downward trend, sensor
  drift or "environmental factor".
- UNSAFE: a downward trend gets a 1-hour remeasure and a "review" contact, with
  no symptom check and no step if the trend continues.

## Rules that passed the checks in this review

- Every rule has a non-empty `contact_ground_text` (no missing contact statement).
- Every red rule names contacting ground now or as soon as the link allows.
- No digits appear in headlines, contributors, action text or contact text,
  except in spo2 rules and `remeasure_after`, as the spec allows.
- No banned diagnosis phrase ("you have", "you are suffering", "diagnosis of",
  "you are sick") appears in the file.

## Recommended next steps (for the safety owner)

1. Decide the emergency-direction wording for red rules and find a sourced
   reference, or link to crew emergency procedures. Do not invent a source.
2. Rewrite diagnosis-like contributors and headlines into symptom or
   measurement language, for example "Sensor placement may be affecting the
   reading" instead of "Breathing issue".
3. Source or remove every TODO action, prioritising the medical-type ones
   listed above.
4. Replace weak source links (`src_otsuka_hrv`, `src_stahn_temp_2017`,
   `src_hera_2020` for mood, `src_nasa_std_3001_v1` for contact timing).
5. Add an explicit crisis/safety pathway to mood.red.
6. Verify the 14 sources (PROGRESS.md) before any rule is shown as sourced.
7. Record the owner's sign-off here, with a name and date, before the app is
   shown to users.

Safety owner sign-off: **[pending: name, date]**
