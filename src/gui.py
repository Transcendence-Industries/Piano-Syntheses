import os
import ast
import logging
import tkinter
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import Tk, Toplevel, Frame, Label, Entry, Button, StringVar, filedialog, messagebox
from tkinter.ttk import Progressbar

from cv import (
    analyse_frames,
    convert_to_midi,
    draw_keys,
    extract_frames,
    get_key_count,
    search_keys,
)

PREVIEW_DIMENSIONS = (960, 540)

DEFAULT_WHITE_COLOR = (255, 255, 255)
DEFAULT_BLACK_COLOR = (0, 0, 0)
DEFAULT_PRESSED_COLOR = (128, 128, 128)

DEFAULT_WHITE_THRESHOLD = 0.25
DEFAULT_BLACK_THRESHOLD = 0.5
DEFAULT_PRESSED_THRESHOLD = 0.55

DEFAULT_MIN_AREA_PIXEL = 500
DEFAULT_MIN_AREA_PERCENT = 0.45
DEFAULT_MIDI_VELOCITY = 64
DEFAULT_NOTE_OFFSET = 21


class MainWindow:
    """Main application window for the conversion workflow."""

    def __init__(self) -> None:
        self.frames = None
        self.props = None
        self.keys = None
        self.piece = None
        self.preview_idx = 0

        self.root = Tk()
        self.root.title("Piano Syntheses - Main")
        self.settings_window = None

        self.video_file = StringVar()
        self.midi_file = StringVar()
        self.preview_image = None
        self.settings = None

        # Input: pick a source video
        frame_input = Frame(master=self.root, borderwidth=10)
        label_input = Label(master=frame_input, text="Input file (video):")
        label_input.grid(row=0, column=0)
        entry_input = Entry(master=frame_input, width=25,
                            state="disabled", textvariable=self.video_file)
        entry_input.grid(row=0, column=1)
        button_input = Button(master=frame_input, text="Browse", width=5, height=1,
                              command=lambda: self.browse_open_file(self.video_file))
        button_input.grid(row=0, column=2)
        frame_input.pack()

        # Extract frames from the video
        frame_extract = Frame(master=self.root, borderwidth=10)
        self.progressbar_extract = Progressbar(master=frame_extract, orient="horizontal", mode="determinate",
                                               length=200)
        self.progressbar_extract.grid(row=0, column=0)
        button_extract = Button(master=frame_extract, text="Extract", width=5, height=1,
                                command=self.extract)
        button_extract.grid(row=0, column=1)
        frame_extract.pack()

        # Preview: step through extracted frames and validate key detection
        frame_preview = Frame(master=self.root, borderwidth=10)
        button_prev = Button(master=frame_preview, text="<", width=5, height=5,
                             command=lambda: self.switch_preview(-10))
        button_prev.grid(row=0, column=0)
        self.label_preview = Label(master=frame_preview)
        self.label_preview.bind("<Button-1>", self.image_click_event)
        self.label_preview.grid(row=0, column=1)
        button_next = Button(master=frame_preview, text=">", width=5, height=5,
                             command=lambda: self.switch_preview(10))
        button_next.grid(row=0, column=2)
        frame_preview.pack()

        # Analyze: run detection across all frames
        frame_analyse = Frame(master=self.root, borderwidth=10)
        self.progressbar_analyse = Progressbar(master=frame_analyse, orient="horizontal", mode="determinate",
                                               length=200)
        self.progressbar_analyse.grid(row=0, column=0)
        button_analyze = Button(master=frame_analyse, text="Analyze", width=5, height=1,
                                command=self.analyze)
        button_analyze.grid(row=0, column=1)
        frame_analyse.pack()

        # Output: select destination MIDI file
        frame_output = Frame(master=self.root, borderwidth=10)
        label_output = Label(master=frame_output, text="Output file (MIDI):")
        label_output.grid(row=1, column=0)
        entry_output = Entry(master=frame_output, width=25,
                             state="disabled", textvariable=self.midi_file)
        entry_output.grid(row=1, column=1)
        button_output = Button(master=frame_output, text="Browse", width=5, height=1,
                               command=lambda: self.browse_save_file(self.midi_file))
        button_output.grid(row=1, column=2)
        frame_output.pack()
        logging.debug("Main window created")

    def update_preview(self, img: any) -> None:
        """Resize and display a frame preview in the GUI."""
        img = Image.fromarray(img).resize(PREVIEW_DIMENSIONS)
        self.preview_image = img
        img = ImageTk.PhotoImage(img)
        self.label_preview.configure(image=img)
        self.label_preview.image = img

    def browse_open_file(self, var: tkinter.Variable) -> None:
        file = filedialog.askopenfilename(
            initialdir=os.getcwd(), title="Open a video")
        var.set(file)

    def browse_save_file(self, var: tkinter.Variable) -> None:
        file = filedialog.asksaveasfilename(
            initialdir=os.getcwd(), title="Save as MIDI")
        var.set(file)

    def extract(self) -> None:
        """Extract frames and initialize the settings window."""
        if self.video_file.get():
            logging.debug("Frame extraction started")
            self.frames, self.props = extract_frames(
                Path(self.video_file.get()), self.progressbar_extract, self.root)
            self.settings_window = SettingsWindow(self)
            self.switch_preview(0)
            logging.info("Frame extraction completed")
        else:
            logging.warning("No video file selected")
            messagebox.showwarning("Warning", "Please select a video!")

    def switch_preview(self, direction: int) -> None:
        """Move the preview cursor and re-run key detection for that frame."""
        if self.frames:
            if self.settings:
                # Prevent out-of-bounds navigation
                if 0 <= self.preview_idx + direction < len(self.frames):
                    self.preview_idx += direction
                    self.keys = search_keys(
                        self.frames[self.preview_idx], self.settings)
                    self.update_preview(
                        draw_keys(self.keys, self.frames[self.preview_idx].copy()))
            else:
                logging.warning("Settings are invalid")
                messagebox.showwarning(
                    "Warning", "The entered settings are invalid!")
        else:
            logging.warning("No frames extracted")
            messagebox.showwarning("Warning", "Please extract frames!")

    def analyze(self) -> None:
        """Run full analysis and export a MIDI file."""
        if self.midi_file.get():
            if self.frames:
                if self.settings:
                    if get_key_count(self.keys) == 88:
                        logging.debug("Analysing started")
                        self.piece = analyse_frames(self.keys, self.frames, self.progressbar_analyse, self.root,
                                                    self.settings)
                        logging.info("Analysing completed")
                        logging.debug("Conversion started")
                        convert_to_midi(self.piece, self.props,
                                        Path(self.midi_file.get()), self.settings)
                        logging.info("Conversion completed")

                        self.settings_window.root.destroy()
                    else:
                        logging.warning("Key count is invalid")
                        messagebox.showwarning(
                            "Warning", "Please switch preview until all keys are detected!")
                else:
                    logging.warning("Settings are invalid")
                    messagebox.showwarning(
                        "Warning", "The entered settings are invalid!")
            else:
                logging.warning("No frames extracted")
                messagebox.showwarning("Warning", "Please extract frames!")
        else:
            logging.warning("No midi file selected")
            messagebox.showwarning("Warning", "Please select a MIDI!")

    def image_click_event(self, event) -> None:
        """Pick an RGB color from the preview for setting calibration."""
        if self.frames:
            rgb = self.preview_image.getpixel((event.x, event.y))
            self.settings_window.selected_color.set(str(rgb))

            logging.debug(
                f"Color {rgb} extracted from preview image at position {event.x}|{event.y}")
            messagebox.showinfo("Info", f"Color {rgb} extracted.")


class SettingsWindow:
    """Parameter controls for color and threshold tuning."""

    def __init__(self, main_window) -> None:
        self.root = Toplevel()
        self.root.title("Piano Syntheses - Settings")
        self.main_window = main_window

        self.selected_color = StringVar()
        self.white_color = StringVar()
        self.white_color.set(str(DEFAULT_WHITE_COLOR))
        self.black_color = StringVar()
        self.black_color.set(str(DEFAULT_BLACK_COLOR))
        self.pressed_color = StringVar()
        self.pressed_color.set(str(DEFAULT_PRESSED_COLOR))
        self.white_threshold = StringVar()
        self.white_threshold.set(str(DEFAULT_WHITE_THRESHOLD))
        self.black_threshold = StringVar()
        self.black_threshold.set(str(DEFAULT_BLACK_THRESHOLD))
        self.pressed_threshold = StringVar()
        self.pressed_threshold.set(str(DEFAULT_PRESSED_THRESHOLD))
        self.min_area_pixel = StringVar()
        self.min_area_pixel.set(str(DEFAULT_MIN_AREA_PIXEL))
        self.min_area_percent = StringVar()
        self.min_area_percent.set(str(DEFAULT_MIN_AREA_PERCENT))
        self.midi_velocity = StringVar()
        self.midi_velocity.set(str(DEFAULT_MIDI_VELOCITY))
        self.note_offset = StringVar()
        self.note_offset.set(str(DEFAULT_NOTE_OFFSET))

        # Colors: define key colors by sampling the preview
        frame_colors = Frame(master=self.root, borderwidth=10)
        label_selected_color = Label(
            master=frame_colors, text="Selected color:")
        label_selected_color.grid(row=0, column=0)
        entry_selected_color = Entry(
            master=frame_colors, width=15, textvariable=self.selected_color)
        entry_selected_color.grid(row=0, column=1)
        label_white_color = Label(master=frame_colors, text="White key color:")
        label_white_color.grid(row=1, column=0)
        entry_white_color = Entry(
            master=frame_colors, width=15, state="disabled", textvariable=self.white_color)
        entry_white_color.grid(row=1, column=1)
        button_white_color = Button(master=frame_colors, text="Set", width=5, height=1,
                                    command=lambda: self.white_color.set(self.selected_color.get()))
        button_white_color.grid(row=1, column=2)
        label_black_color = Label(master=frame_colors, text="Black key color:")
        label_black_color.grid(row=2, column=0)
        entry_black_color = Entry(
            master=frame_colors, width=15, state="disabled", textvariable=self.black_color)
        entry_black_color.grid(row=2, column=1)
        button_black_color = Button(master=frame_colors, text="Set", width=5, height=1,
                                    command=lambda: self.black_color.set(self.selected_color.get()))
        button_black_color.grid(row=2, column=2)
        label_pressed_color = Label(
            master=frame_colors, text="Pressed key color:")
        label_pressed_color.grid(row=3, column=0)
        entry_pressed_color = Entry(
            master=frame_colors, width=15, state="disabled", textvariable=self.pressed_color)
        entry_pressed_color.grid(row=3, column=1)
        button_pressed_color = Button(master=frame_colors, text="Set", width=5, height=1,
                                      command=lambda: self.pressed_color.set(self.selected_color.get()))
        button_pressed_color.grid(row=3, column=2)
        frame_colors.pack()

        # Thresholds: configure tolerance for color matching
        frame_thresholds = Frame(master=self.root, borderwidth=10)
        label_white_threshold = Label(
            master=frame_thresholds, text="White key threshold:")
        label_white_threshold.grid(row=0, column=0)
        entry_white_threshold = Entry(
            master=frame_thresholds, width=10, textvariable=self.white_threshold)
        entry_white_threshold.grid(row=0, column=1)
        label_black_threshold = Label(
            master=frame_thresholds, text="Black key threshold:")
        label_black_threshold.grid(row=1, column=0)
        entry_black_threshold = Entry(
            master=frame_thresholds, width=10, textvariable=self.black_threshold)
        entry_black_threshold.grid(row=1, column=1)
        label_pressed_threshold = Label(
            master=frame_thresholds, text="Pressed key threshold:")
        label_pressed_threshold.grid(row=2, column=0)
        entry_pressed_threshold = Entry(
            master=frame_thresholds, width=10, textvariable=self.pressed_threshold)
        entry_pressed_threshold.grid(row=2, column=1)
        frame_thresholds.pack()

        # Detection and MIDI parameters
        frame_other = Frame(master=self.root, borderwidth=10)
        label_min_area_pixel = Label(
            master=frame_other, text="Minimum area for key-contour detection (in pixels):")
        label_min_area_pixel.grid(row=0, column=0)
        entry_min_area_pixel = Entry(
            master=frame_other, width=10, textvariable=self.min_area_pixel)
        entry_min_area_pixel.grid(row=0, column=1)
        label_min_area_percent = Label(
            master=frame_other, text="Minimum area for key-press detection (in percent):")
        label_min_area_percent.grid(row=1, column=0)
        entry_min_area_percent = Entry(
            master=frame_other, width=10, textvariable=self.min_area_percent)
        entry_min_area_percent.grid(row=1, column=1)
        label_midi_velocity = Label(
            master=frame_other, text="MIDI velocity (0-127):")
        label_midi_velocity.grid(row=2, column=0)
        entry_midi_velocity = Entry(
            master=frame_other, width=10, textvariable=self.midi_velocity)
        entry_midi_velocity.grid(row=2, column=1)
        label_note_offset = Label(master=frame_other, text="Note offset:")
        label_note_offset.grid(row=3, column=0)
        entry_note_offset = Entry(
            master=frame_other, width=10, textvariable=self.note_offset)
        entry_note_offset.grid(row=3, column=1)
        frame_other.pack()

        button_refresh = Button(
            master=self.root, text="Refresh", width=5, height=1, command=self.refresh)
        button_refresh.pack()

        logging.debug("Settings window created")
        self.main_window.settings = self.get_settings()

    def refresh(self) -> None:
        """Update settings from the form and refresh the preview."""
        self.main_window.settings = self.get_settings()
        self.main_window.switch_preview(0)

    def get_settings(self) -> dict[str, any]:
        """Parse and validate settings from the UI fields."""
        settings = {}

        try:
            settings["white_color"] = ast.literal_eval(self.white_color.get())
            settings["black_color"] = ast.literal_eval(self.black_color.get())
            settings["pressed_color"] = ast.literal_eval(
                self.pressed_color.get())

            # Convert RGB to BGR
            settings["white_color"] = settings["white_color"][::-1]
            settings["black_color"] = settings["black_color"][::-1]
            settings["pressed_color"] = settings["pressed_color"][::-1]

            settings["white_threshold"] = float(self.white_threshold.get())
            settings["black_threshold"] = float(self.black_threshold.get())
            settings["pressed_threshold"] = float(self.pressed_threshold.get())

            settings["min_area_pixel"] = int(self.min_area_pixel.get())
            settings["min_area_percent"] = float(self.min_area_percent.get())
            settings["midi_velocity"] = int(self.midi_velocity.get())
            settings["note_offset"] = int(self.note_offset.get())
        except:
            return None

        if any(not value for value in settings.values()):
            return None

        return settings
