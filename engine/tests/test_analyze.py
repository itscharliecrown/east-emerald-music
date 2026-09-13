import numpy as np
import pytest

from engine.analyze import analyze, clipping_runs, silent_bars
from engine.analyze.key import estimate_key, semitone_distance
from engine.analyze.tempo import estimate_tempo, fold_to_target
from engine.analyze.tuning import estimate_tuning_cents
from tests.synth import SR, chord_loop


@pytest.mark.parametrize("bpm", [72, 90, 124])
def test_tempo_within_two_percent(bpm):
    x = chord_loop("E", "minor", bpm, bars=8)
    t = estimate_tempo(x.mean(axis=0), SR, target_bpm=bpm, backend="librosa")
    assert t.error_pct(bpm) < 2.0, t
    assert t.drift_cv < 0.03


def test_fold_to_target():
    assert fold_to_target(180, 90) == 90
    assert fold_to_target(45, 90) == 90
    assert fold_to_target(92, 90) == 92


@pytest.mark.parametrize("tonic,mode", [("E", "minor"), ("D", "major"), ("Bb", "major"), ("A", "minor")])
def test_key_detection(tonic, mode):
    x = chord_loop(tonic, mode, 90, bars=8)
    k = estimate_key(x.mean(axis=0), SR)
    assert (k.tonic, k.mode) == (tonic, mode), k


def test_semitone_distance_is_shortest_path():
    assert semitone_distance(0, 2) == 2
    assert semitone_distance(0, 11) == -1
    assert semitone_distance(4, 2) == -2


def test_tuning_offset_detected():
    x = chord_loop("C", "major", 90, bars=4, a4=440.0)
    assert abs(estimate_tuning_cents(x.mean(axis=0), SR)) < 8
    x = chord_loop("C", "major", 90, bars=4, a4=440.0 * 2 ** (25 / 1200))  # +25 cents
    c = estimate_tuning_cents(x.mean(axis=0), SR)
    assert 15 < c < 35, c


def test_clipping_and_silence():
    x = chord_loop("C", "major", 90, bars=4)
    assert clipping_runs(x) == 0
    x[:, 1000:1010] = 1.0
    assert clipping_runs(x) == 1
    bar = int(round(4 * 60 / 90 * SR))
    y = chord_loop("C", "major", 90, bars=4)
    y[:, :bar] = 0
    assert silent_bars(y, bar) == 1


def test_full_analysis_runs():
    x = chord_loop("E", "minor", 90, bars=4)
    a = analyze(x, SR, target_bpm=90, bar_samples=int(round(4 * 60 / 90 * SR)))
    assert a.key.tonic == "E"
    assert a.loudness.lufs < 0
    assert -1.0 <= a.stereo_correlation <= 1.0
