import pytest

from engine.conform.stretch import rubberband, rubberband_available
from tests.synth import SR, chord_loop


def test_identity_is_passthrough():
    x = chord_loop("C", "major", 90, bars=2)
    assert rubberband(x, SR) is x


@pytest.mark.skipif(not rubberband_available(), reason="rubberband CLI not installed locally")
def test_stretch_changes_length():
    x = chord_loop("C", "major", 90, bars=2)
    y = rubberband(x, SR, time_ratio=1.05)
    assert abs(y.shape[1] / x.shape[1] - 1.05) < 0.01
