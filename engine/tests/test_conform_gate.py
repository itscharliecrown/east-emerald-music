import numpy as np

from engine.analyze import analyze
from engine.conform.level import normalize_level
from engine.conform.window import cut_loop, find_loop_window
from engine.export import loop_filename
from engine.gate import evaluate
from engine.spec import Instrument, Key, LoopSpec, loop_samples
from tests.synth import SR, chord_loop


def _spec(bpm=90, tonic="E", mode="minor", bars=4) -> LoopSpec:
    return LoopSpec(instrument=Instrument(family="piano", type="upright_piano"), genre="Lo-Fi Hip Hop",
                    moods=["warm"], key=Key(tonic=tonic, mode=mode), bpm=bpm, bars=bars)


def test_window_search_finds_a_downbeat_and_cuts_exact_length():
    spec = _spec()
    x = chord_loop("E", "minor", 90, bars=4, pre_roll_bars=1, tail_bars=1)
    mono = x.mean(axis=0)
    a = analyze(x, SR, target_bpm=90)
    n = loop_samples(4, 90)
    w = find_loop_window(mono, SR, loop_samples=n, bars=4, downbeats_s=a.tempo.downbeats)
    loop = cut_loop(x, SR, start=w.start_sample, loop_samples=n)
    assert loop.shape == (2, n)
    # start lands close to a bar boundary of the synthetic grid (1 bar pre-roll = 2.667 s)
    bar_s = 4 * 60 / 90
    assert abs((w.start_sample / SR) % bar_s) < 0.06 or abs((w.start_sample / SR) % bar_s - bar_s) < 0.06


def test_normalize_hits_target_without_exceeding_ceiling():
    x = chord_loop("E", "minor", 90, bars=4) * 0.1
    y, info = normalize_level(x, SR)
    a = analyze(y, SR, rhythmic=False)
    assert a.loudness.true_peak_dbtp <= -0.9
    assert abs(a.loudness.lufs - (-16.0)) < 1.5 or info["ceiling_bound"]


def test_gate_passes_matching_clip_and_rejects_wrong_key():
    x = chord_loop("E", "minor", 90, bars=4)
    a = analyze(x, SR, target_bpm=90, bar_samples=loop_samples(1, 90))
    g = evaluate(_spec(), a)
    assert g.passed, g
    assert g.key_shift_semitones == 0

    g2 = evaluate(_spec(tonic="Bb"), a)   # 6 semitones away
    assert not g2.passed and "key_mismatch" in g2.reasons


def test_gate_rejects_tempo_out_of_range():
    x = chord_loop("E", "minor", 100, bars=4)
    a = analyze(x, SR, target_bpm=90)
    g = evaluate(_spec(bpm=90), a)
    assert "tempo_out_of_range" in g.reasons


def test_filename_convention():
    name = loop_filename(_spec(bpm=80, bars=8), descriptor="warm", id4="7f3a")
    assert name == "EE_UprightPiano_Warm_Emin_80BPM_8bar_7f3a.wav"
