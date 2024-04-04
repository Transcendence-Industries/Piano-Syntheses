from PIL import Image, ImageTk
from tkinter import Tk, Frame, Label, Entry, Button, StringVar, filedialog, messagebox
from tkinter.ttk import Progressbar

from processing import *

PREVIEW_DIMENSIONS = (960, 540)


class App:
    def __init__(self):
        self.frames = None
        self.props = None
        self.keys = None
        self.piece = None
        self.preview = 0

        self.root = Tk()
        self.root.title("Piano Syntheses")
        # self.root.resizable(False, False)

        self.video_file = StringVar()
        self.midi_file = StringVar()

        # Input frame
        frame_input = Frame(master=self.root, borderwidth=10)
        label_input = Label(master=frame_input, text="Input file (video):")
        label_input.grid(row=0, column=0)
        entry_input = Entry(master=frame_input, width=25, state="disabled", textvariable=self.video_file)
        entry_input.grid(row=0, column=1)
        button_input = Button(master=frame_input, text="Browse", width=5, height=1,
                              command=lambda: self.browse_open_file(self.video_file))
        button_input.grid(row=0, column=2)
        frame_input.pack()

        # Extract frame
        frame_extract = Frame(master=self.root, borderwidth=10)
        self.progressbar_extract = Progressbar(master=frame_extract, orient="horizontal", mode="determinate",
                                               length=200)
        self.progressbar_extract.grid(row=0, column=0)
        button_extract = Button(master=frame_extract, text="Extract", width=5, height=1,
                                command=self.extract)
        button_extract.grid(row=0, column=1)
        frame_extract.pack()

        # Preview frame
        frame_preview = Frame(master=self.root, borderwidth=10)
        button_prev = Button(master=frame_preview, text="<", width=5, height=5,
                             command=lambda: self.switch_preview(-10))
        button_prev.grid(row=0, column=0)
        self.label_preview = Label(master=frame_preview)
        self.label_preview.grid(row=0, column=1)
        button_next = Button(master=frame_preview, text=">", width=5, height=5,
                             command=lambda: self.switch_preview(10))
        button_next.grid(row=0, column=2)
        frame_preview.pack()

        # Analyse frame
        frame_analyse = Frame(master=self.root, borderwidth=10)
        self.progressbar_analyse = Progressbar(master=frame_analyse, orient="horizontal", mode="determinate",
                                               length=200)
        self.progressbar_analyse.grid(row=0, column=0)
        button_analyze = Button(master=frame_analyse, text="Analyze", width=5, height=1,
                                command=self.analyze)
        button_analyze.grid(row=0, column=1)
        frame_analyse.pack()

        # Output frame
        frame_output = Frame(master=self.root, borderwidth=10)
        label_output = Label(master=frame_output, text="Output file (MIDI):")
        label_output.grid(row=1, column=0)
        entry_output = Entry(master=frame_output, width=25, state="disabled", textvariable=self.midi_file)
        entry_output.grid(row=1, column=1)
        button_output = Button(master=frame_output, text="Browse", width=5, height=1,
                               command=lambda: self.browse_save_file(self.midi_file))
        button_output.grid(row=1, column=2)
        frame_output.pack()
        logging.info("Gui created")

    def update_preview(self, img):
        img = ImageTk.PhotoImage(Image.fromarray(img).resize(PREVIEW_DIMENSIONS))
        self.label_preview.configure(image=img)
        self.label_preview.image = img

    def browse_open_file(self, var):
        file = filedialog.askopenfilename(initialdir=os.getcwd(), title="Open a video")
        var.set(file)

    def browse_save_file(self, var):
        file = filedialog.asksaveasfilename(initialdir=os.getcwd(), title="Save as MIDI")
        var.set(file)

    def extract(self):
        # Check if video file is selected
        if self.video_file.get():
            logging.info("Frame extraction started")
            self.frames, self.props = extract_frames(self.video_file.get(), self.progressbar_extract, self.root)
            self.switch_preview(0)
            logging.info("Frame extraction completed")
        else:
            logging.warning("No video file selected")
            messagebox.showwarning("Warning", "Please select a video!")

    def switch_preview(self, direction):
        # Check if frames are extracted
        if self.frames:
            # Check if preview can be switched
            if 0 <= self.preview + direction < len(self.frames):
                self.preview += direction
                self.keys = search_keys(self.frames[self.preview])
                self.update_preview(draw_keys(self.keys, self.frames[self.preview].copy()))
        else:
            logging.warning("No frames extracted")
            messagebox.showwarning("Warning", "Please extract frames!")

    def analyze(self):
        # Check if midi file is selected and frames are extracted
        if self.midi_file.get():
            if self.frames:
                if get_key_count(self.keys) == 88:
                    logging.info("Analysing started")
                    self.piece = analyse_frames(self.keys, self.frames, self.progressbar_analyse, self.root)
                    logging.info("Analysing completed")
                    logging.info("Conversion started")
                    convert_to_midi(self.piece, self.props, self.midi_file.get())
                    logging.info("Conversion completed")
                else:
                    logging.warning("Key count is invalid")
                    messagebox.showwarning("Warning", "Please switch preview until all keys are detected!")
            else:
                logging.warning("No frames extracted")
                messagebox.showwarning("Warning", "Please extract frames!")
        else:
            logging.warning("No midi file selected")
            messagebox.showwarning("Warning", "Please select a MIDI!")
