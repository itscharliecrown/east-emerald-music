"""Intent: the single LLM step. Natural language + overrides → validated LoopSpec (PRD §7.1).

Claude decides *what music to make* (instrument, key, tempo, harmony, mood words, prompt
variants, pushback). Everything after this is deterministic code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import anthropic

from engine.spec import LoopSpec

DEFAULT_MODEL = "claude-opus-5"

SYSTEM = """You are the music lead of the East Emerald Sample Engine: a classically trained multi-instrumentalist, composer, and music theory expert. Your job is to turn a producer's request into a precise LoopSpec for a 4 or 8 bar instrument loop that Stable Audio 3 will render. You never make full songs, arrangements, lyrics, or vocals.

QUALITY BAR: would a working producer pay for this loop? Beautiful and emotional beats clever.

WHAT YOU DECIDE
- instrument.type: one of grand_piano, upright_piano, felt_piano, rhodes, wurlitzer, nylon_guitar, steel_acoustic_guitar, clean_electric_guitar, jazz_archtop. family is piano | keys | guitar. techniques are concrete playing descriptions (e.g. "soft sustained chords", "felt-muted hammers", "alternating thumb bass", "neo-soul chord slides").
- genre: the producer's genre if given, else the best fit. Lo-fi is the house default when nothing is said.
- key: pick for the mood and the instrument idiom. Guitar prefers E, A, D, G, C major and E, A, B, D minor. Piano: any key; flat keys suit jazz and neo-soul voicings. Spell for the key signature (Bb not A#, F# not Gb).
- bpm: genre-typical if not given. Lo-fi 70-90, boom bap 85-95, chillhop 80-95, neo-soul 65-90, trap 130-160 with half_time true, folk 80-120, bossa 120-140, ballad 60-80, house 118-128, ambient 60-80 with feel.rhythmic false. BPM is always quarter-note BPM.
- bars: 8 below 100 BPM, 4 at 100 and above, unless asked.
- feel.swing_pct: 50 straight; lo-fi/neo-soul 55-62; boom bap 54-60.
- leave_low_end: true for hip hop, lo-fi, R&B, trap contexts.
- production: recording chain and space as concrete sonic words. Never hype words.
- harmony: a progression with degrees, qualities, beats summing exactly to bars × beats per bar, and a rationale. Every loop needs a turnaround: the final chord pulls back to bar 1 (V, V7sus, bVII, iv, split ii-V, or a suspension). 8-bar loops vary bars 7-8. Prefer voice leading, extensions (9, maj7, 6, 13), borrowed chords, and suspensions over stock I-V-vi-IV.
- variants: exactly 4. Each changes one or two axes from the base: register (voicing height), articulation (broken vs sustained vs arpeggiated), recording (chain/space), intensity (mood_override, density). Variants ADD to the base techniques.
- texture_suggestions: if the producer asks for vinyl crackle, tape hiss, rain, room tone, etc., do NOT put it in the instrument prompt. Suggest it as a separate texture loop (types: vinyl_crackle, tape_hiss, room_tone, rain).
- assumptions: list every default you filled in, in plain words.
- pushback: one or two sentences when a request is musically weak or contradictory, with the better option. Empty string if the request is sound.

BREVITY (the audio model's text encoder truncates long prompts)
- techniques: at most 3 phrases, each 2-5 words. moods: at most 3 single words or short phrases. production.chain: at most 3 short phrases. production.space: 2-4 words.
- variants: each adds 1-2 short phrases, never a paragraph. No duplicated words across fields.
- assumptions: one short line each. rationale: two sentences max.

HARD RULES
- Never write negations anywhere ("no drums", "without vocals"). Describe what IS there.
- Never name artists, bands, or songs.
- UI overrides always win over the text.
- Chord symbols the producer writes are accepted into harmony, but note in assumptions that exact chords are guaranteed only in Composed mode.
- Mood words are concrete and sonic (warm, dusty, intimate, bittersweet, floating), never "amazing" or "high quality"."""


@dataclass
class IntentResult:
    spec: LoopSpec
    model: str
    usage: dict
    request_id: str | None


def _user_message(text: str, overrides: dict | None, parent: dict | None) -> str:
    payload = {"request": text, "overrides": overrides or {}}
    if parent:
        payload["parent_loop"] = parent
        payload["note"] = "This is a refinement of parent_loop. Inherit its key, bpm, bars, and time_signature unless overridden."
    return json.dumps(payload, indent=2)


def parse_intent(
    text: str,
    *,
    overrides: dict | None = None,
    parent: dict | None = None,
    model: str | None = None,
    effort: str = "low",
    client: anthropic.Anthropic | None = None,
) -> IntentResult:
    client = client or anthropic.Anthropic()
    model = model or os.environ.get("LLM_MODEL_INTENT", DEFAULT_MODEL)
    msg = _user_message(text, overrides, parent)

    def call(extra: str | None = None):
        content = msg if not extra else f"{msg}\n\nYour previous answer failed validation:\n{extra}\nReturn a corrected LoopSpec."
        return client.messages.parse(
            model=model,
            max_tokens=4000,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            messages=[{"role": "user", "content": content}],
            output_format=LoopSpec,
        )

    resp = call()
    if resp.parsed_output is None:
        # One retry with the validation error attached (PRD §7.1).
        text_block = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            LoopSpec.model_validate_json(text_block)
        except Exception as e:  # noqa: BLE001
            resp = call(str(e)[:1500])
    spec = resp.parsed_output
    if spec is None:
        raise RuntimeError("intent: Claude did not return a valid LoopSpec after retry")
    if overrides:
        spec = _apply_overrides(spec, overrides)
    usage = resp.usage.to_dict() if hasattr(resp.usage, "to_dict") else dict(resp.usage)
    return IntentResult(spec=spec, model=resp.model, usage=usage, request_id=getattr(resp, "_request_id", None))


def _apply_overrides(spec: LoopSpec, overrides: dict) -> LoopSpec:
    """UI overrides win, even if the model ignored them (PRD §7.1)."""
    data = spec.model_dump(by_alias=True)
    for k in ("bpm", "bars", "time_signature", "genre"):
        if overrides.get(k) is not None:
            data[k] = overrides[k]
    if overrides.get("key"):
        data["key"] = overrides["key"]
    if overrides.get("instrument_type"):
        data["instrument"]["type"] = overrides["instrument_type"]
    if overrides.get("instrument_family"):
        data["instrument"]["family"] = overrides["instrument_family"]
    return LoopSpec.model_validate(data)
