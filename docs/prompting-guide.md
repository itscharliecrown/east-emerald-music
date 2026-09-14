# Prompting the East Emerald Sample Engine

You are not prompting Stable Audio. You are briefing a musician (Claude) who then briefs the instrument (Stable Audio 3). Write the brief the way you'd talk to a session player.

## The one rule
**Say what you hear, in the order a producer would.** Instrument → how it's played → feeling → key/tempo → recording. Everything else is optional.

Good: `felt piano, slow broken chords, bittersweet, E minor, 78, cassette`
Weak: `amazing lo-fi piano loop high quality`

## What each part does

| Part | Example | Who uses it |
|---|---|---|
| Instrument | felt piano, upright, Rhodes, nylon guitar, clean electric | Both. The single most important word. |
| Playing | soft sustained chords, broken chords, fingerpicked, chord stabs, arpeggios | Both. Drives the MIDI pattern in Composed mode. |
| Feeling | bittersweet, nostalgic, hopeful, late-night, floating | Claude turns it into harmony (§10.2 of the PRD). SA3 turns it into tone. |
| Key + tempo | E minor, 80 | Claude. Exact in Composed mode; measured and corrected in Prompt mode. |
| Recording | close-miked, tape, small room, ribbon mic, spring reverb | SA3 only. Concrete words beat adjectives. |
| Chords | `im9 · ivm7 · bVIImaj7 · v7sus4` or `Em9 Am7 Dmaj7 B7sus4` | Claude. **Only exact in Composed mode.** |

## Composed vs Prompt mode
- **Composed (default):** Claude writes the progression, we render it to MIDI, SA3 re-voices that audio. The chords are the chords. You get the MIDI. Use this for song starters.
- **Prompt:** SA3 improvises from words alone. More surprising, less controllable, no MIDI. Use it when you want the model's own ideas or a texture.

**Timbre freedom** (Composed mode slider, 0.25–0.75): how far SA3 may drift from the MIDI render. 0.35 keeps every note but can sound synthetic. 0.55 sounds more like a real recording but may bend a voicing. Start at 0.45.

## Complexity
- **basic:** triads, one chord per bar. Clean, safe, wide open for a topline.
- **medium:** 7ths and 9ths, one borrowed chord or suspension. The lo-fi default.
- **complex:** extended and altered chords, chromatic approaches, split-bar ii–V. `im9 · ivm7 · bVIImaj7 · bVImaj7 · v7sus4` lives here.

## Writing chords yourself
Roman numerals or symbols both work. Accidentals are relative to the major scale, so in E minor `bVII` is D and `bVI` is C. Durations are split evenly unless you write them: `Em9(2 bars) Am7 B7sus4`.

## Lo-fi piano recipes that work
- `felt piano, soft broken chords, nostalgic, E minor, 78` → medium, pattern broken
- `upright piano, sustained jazzy chords with light pedal blur, warm and dusty, F major, 82` → complex
- `Rhodes, warm tremolo chords, late-night, Eb major, 76` → medium, pattern sustained
- `grand piano, slow arpeggios, cinematic and sad, D minor, 70, concert hall` → medium, pattern arpeggio

## Lo-fi guitar recipes that work
- `nylon guitar, fingerpicked, intimate, A minor, 84, close mic` → medium, fingerstyle
- `clean electric guitar, neo-soul chord slides, smooth, C minor, 84, spring reverb` → complex, broken
- `steel acoustic, gentle strum, hopeful, D major, 96` → basic, strum

## Things that hurt
- Negations ("no drums"). The encoder can't read "no". The engine rejects them.
- Artist or song names. Rejected.
- Genre words for hip hop in the SA3 prompt. The engine strips them because they summon drums. Say "lo-fi, dusty" instead; the engine does this for you.
- Long prompts. Past ~80 words the model stops reading. Say less, more precisely.
- Asking for a full song, a melody line with lyrics, or "verse and chorus". This is a loop engine.

## Reading the results
- **Requested vs got:** the engine measures tempo and key on every clip and shows the correction it applied ("shifted +2 st"). Big corrections mean the model fought the request; try a different key or tempo nearby.
- **Harmony score** (Composed mode): how closely the audio kept the composed chords. Below 0.75 is rejected.
- **Nothing passed:** the model wandered. Lower timbre freedom, or simplify.
