# Pipeline Overview

This document summarizes the core algorithm used by Piano Syntheses.

## 1. Frame Extraction

The input video is decoded with OpenCV. Every frame is stored in memory so the analysis step can iterate deterministically. Basic properties are captured (dimensions, fps, frame count) to drive MIDI timing later.

## 2. Key Detection (Single Frame)

The keyboard is detected once on a selected preview frame:

- Two masks are built using a white-key color and a black-key color.
- Contours are extracted for both masks.
- Bounding rectangles below a minimum area threshold are filtered out.
- The remaining rectangles are sorted by x-position.
- The list is mapped onto a canonical 88-key order.

If fewer than 88 keys are detected, placeholders are inserted and the GUI warns the user.

## 3. Pressed Key Detection (Per Frame)

For every frame:

- A pressed-key mask is built using the sampled pressed color.
- Each key rectangle is checked for sufficient “pressed” pixel coverage.
- The result is a per-frame dictionary of pressed states for all 88 notes.

## 4. MIDI Conversion

The per-frame note states are compared with the previous frame to detect transitions. Each change is turned into a `note_on` or `note_off` MIDI event. Timing is derived from the video fps so that playback aligns with the original tempo.
