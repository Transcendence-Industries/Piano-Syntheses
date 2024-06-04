# Settings Guide

This document explains the GUI controls and how to tune them.

## Color Sampling

Click on the preview image to sample an RGB value. Use the “Set” buttons to assign that value to:

- White key color
- Black key color
- Pressed key color

Internally, colors are converted to BGR because OpenCV uses BGR ordering.

## Thresholds

Thresholds define how much each sampled color can vary and still be detected.

- White key threshold: tolerance for white-key detection
- Black key threshold: tolerance for black-key detection
- Pressed key threshold: tolerance for pressed-key detection

Larger values are more tolerant but can introduce false positives.

## Area Filters

- Minimum area for key-contour detection (pixels): removes small noise contours.
- Minimum area for key-press detection (percent): required fraction of a key rectangle that must be “pressed” to trigger a note.

## MIDI Parameters

- MIDI velocity: fixed velocity used for all notes (0–127).
- Note offset: base note number (A0 is 21 in standard MIDI).
