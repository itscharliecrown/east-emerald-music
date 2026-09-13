"""Conformance: make a raw generation sample-accurate, in key, in tune, seamless, and level (PRD §7.6)."""

from engine.conform.level import normalize_level
from engine.conform.stretch import rubberband
from engine.conform.window import cut_loop, find_loop_window

__all__ = ["rubberband", "find_loop_window", "cut_loop", "normalize_level"]
