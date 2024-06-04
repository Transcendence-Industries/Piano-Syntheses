import os
import cv2
import mido
import numpy as np
from mido import MidiFile, MidiTrack, Message

from log import logger

KEYBOARD = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def extract_frames(path, progress, window):
    # Get video properties
    video = cv2.VideoCapture(path)
    dim = (video.get(cv2.CAP_PROP_FRAME_WIDTH), video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = video.get(cv2.CAP_PROP_FPS)
    length = video.get(cv2.CAP_PROP_FRAME_COUNT)
    logger.info(f"Video '{os.path.basename(path)}' loaded")
    logger.info(f"> Dimensions: {dim}")
    logger.info(f"> FPS: {fps}")
    logger.info(f"> Length: {length} frames ({int(length / fps)} seconds)")

    ret = True
    frames = []
    frame_num = 0
    progress["value"] = 0
    window.update_idletasks()

    # While video is providing frames
    while ret:
        ret, frame = video.read()

        if ret:
            frames.append(frame)
            frame_num += 1

            # Update progress every 100 frames
            if frame_num % 100 == 0:
                progress["value"] = frame_num / length * 100
                window.update_idletasks()
                logger.info(f"Frame {frame_num} extracted")

    progress["value"] = 100
    window.update_idletasks()
    props = {"dim": dim, "fps": fps, "length": length}
    return frames, props


def get_color_ranges(color, scalar):
    # Round between 0 and 255
    lower = tuple(min(255, max(0, round(c - c * scalar))) for c in color)
    higher = tuple(min(255, max(0, round(c + c * scalar))) for c in color)
    return lower, higher


def get_key_dict(fill):
    # First keys
    keys = {"A0": fill,
            "A#0": fill,
            "B0": fill}

    # 7 full octaves
    for i in range(7):
        for note in KEYBOARD:
            if note in ("A", "A#", "B"):
                keys[note + str(i + 1)] = fill
            else:
                keys[note + str(i)] = fill

    # Last key
    keys["C7"] = fill
    return keys


def get_key_count(keys):
    count = 0

    # Loop over keys
    for note, (x, y, w, h) in keys.items():
        # Check if key is not a placeholder
        if w * h > 0:
            count += 1

    return count


def search_keys(frame, settings):
    # Define masks
    white_mask = cv2.inRange(frame, *get_color_ranges(settings["white_color"], settings["white_threshold"]))
    black_mask = cv2.inRange(frame, *get_color_ranges(settings["black_color"], settings["black_threshold"]))

    # Find contours
    white_keys = cv2.findContours(white_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    black_keys = cv2.findContours(black_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    white_keys = [cv2.boundingRect(i) for i in white_keys]
    black_keys = [cv2.boundingRect(i) for i in black_keys]

    # Filter contours
    white_keys = [(x, y, w, h) for x, y, w, h in white_keys if w * h > settings["min_area_pixel"]]
    black_keys = [(x, y, w, h) for x, y, w, h in black_keys if w * h > settings["min_area_pixel"]]

    # Sort by x coordinate
    white_keys = sorted(white_keys, key=lambda x: x[0])
    black_keys = sorted(black_keys, key=lambda x: x[0])

    logger.info(f"Found {len(white_keys + black_keys)} keys ({len(white_keys)} white, {len(black_keys)} black)")
    if len(white_keys + black_keys) != 88:
        logger.warning(f"Key count is not equal to 88")

    white_index = 0
    black_index = 0
    keys = get_key_dict(None)

    # Loop over keys
    for note in keys.keys():
        if "#" in note and black_index < len(black_keys):  # Black key
            keys[note] = black_keys[black_index]
            black_index += 1
        elif white_index < len(white_keys):  # White key
            keys[note] = white_keys[white_index]
            white_index += 1
        else:  # Placeholder
            keys[note] = (0, 0, 0, 0)

    return keys


def draw_keys(keys, img):
    # Loop over keys
    for note, (x, y, w, h) in keys.items():
        if "#" in note:  # Black key
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
        else:  # White key
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # Draw key count
    length = get_key_count(keys)
    if length == 88:
        cv2.putText(img, f"Keys: {length}/88", org=(50, 50), color=(0, 255, 0),
                    fontScale=1, fontFace=0, thickness=2)
    else:
        cv2.putText(img, f"Keys: {length}/88", org=(50, 50), color=(255, 0, 0),
                    fontScale=1, fontFace=0, thickness=2)

    return img


def analyse_frame(keys, frame, settings):
    pressed = get_key_dict(False)
    mask = cv2.inRange(frame, *get_color_ranges(settings["pressed_color"], settings["pressed_threshold"]))
    detected = cv2.bitwise_and(frame, frame, mask=mask)

    # Loop over keys
    for note, (x, y, w, h) in keys.items():
        # Check if box is not a placeholder
        if w * h > 0:
            box = detected[y:y + h, x:x + w]
            color = np.count_nonzero(box)

            # Check if key is pressed
            if color / (w * h) >= settings["min_area_percent"]:
                pressed[note] = True

    return pressed


def analyse_frames(keys, frames, progress, window, settings):
    piece = []

    # Loop over frames
    for i, frame in enumerate(frames):
        pressed = analyse_frame(keys, frame, settings)
        piece.append(pressed)

        # Update progress every 100 frames
        if i % 100 == 0:
            progress["value"] = i / len(frames) * 100
            window.update_idletasks()
            logger.info(f"Frame {i} analysed")

    progress["value"] = 100
    window.update_idletasks()
    return piece


def convert_to_midi(piece, props, path, settings):
    # Initial setup
    track = MidiTrack()
    midi = MidiFile(type=0)
    midi.tracks.append(track)
    track.append(Message("program_change", program=0, time=0))

    previous = get_key_dict(False)
    messages = 0
    delay = 0

    # Loop over piece
    for time, pressed in enumerate(piece):
        delay += 1

        # Loop over notes
        for key, (note, state) in enumerate(pressed.items()):
            # Check if note changed
            if state != previous[note]:
                ticks = int(mido.second2tick(1 / props["fps"], midi.ticks_per_beat, 500000) * delay)

                if state:  # Note pressed
                    track.append(
                        Message("note_on", note=settings["note_offset"] + key, velocity=settings["midi_velocity"],
                                time=ticks))
                else:  # Note released
                    track.append(
                        Message("note_off", note=settings["note_offset"] + key, velocity=settings["midi_velocity"],
                                time=ticks))

                delay = 0
                messages += 1

        previous = pressed.copy()

        # Update progress every 100 times
        if time % 100 == 0:
            logger.info(f"Timing {time} converted")

    midi.save(path)
    logger.info(f"MIDI '{os.path.basename(path)}' saved ({messages} messages)")
