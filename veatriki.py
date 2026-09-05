#!/usr/bin/env python3
"""
search_packhum_gui.py - Beautiful GUI interface for searching iphi.json using tkinter
"""

import json
import csv
import re
import unicodedata
import xml.etree.ElementTree as ET
from xml.dom import minidom
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from tkinter import BooleanVar, StringVar
from collections import defaultdict
import threading
from pathlib import Path
from datetime import datetime

# Roman numeral ↔ Arabic numeral mapping (I=1 … XXX=30)
_ROMAN_MAP = [
    (1,'I'),(2,'II'),(3,'III'),(4,'IV'),(5,'V'),
    (6,'VI'),(7,'VII'),(8,'VIII'),(9,'IX'),(10,'X'),
    (11,'XI'),(12,'XII'),(13,'XIII'),(14,'XIV'),(15,'XV'),
    (16,'XVI'),(17,'XVII'),(18,'XVIII'),(19,'XIX'),(20,'XX'),
    (21,'XXI'),(22,'XXII'),(23,'XXIII'),(24,'XXIV'),(25,'XXV'),
    (26,'XXVI'),(27,'XXVII'),(28,'XXVIII'),(29,'XXIX'),(30,'XXX'),
]
_ROMAN_TO_INT = {r: n for n, r in _ROMAN_MAP}
_INT_TO_ROMAN = {n: r for n, r in _ROMAN_MAP}


class PackhumSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🏛️ Veatriki")
        self.root.geometry("1400x900")

        # Configure style
        self.setup_styles()

        # Data storage
        self.data = None
        self.current_results = []
        self.dark_mode = False

        # Search enhancement state
        self.input_mode_var = StringVar(value='greek')
        self.use_regex_var = BooleanVar(value=False)
        self.ignore_signs_var = BooleanVar(value=False)
        self.book_name_var = StringVar()
        self.book_ref_var = StringVar()
        self.normalized_text_cache = None
        self.normalized_words_cache = None
        self.bare_text_cache = None
        self.latin_text_cache = None
        self.bare_latin_text_cache = None
        self._result_scores = {}

        # Create main scrollable canvas
        self.create_scrollable_canvas()

        # Create GUI
        self.create_menu()
        self.create_header()
        self.create_search_frame()
        self.create_results_frame()
        self.create_export_frame()
        self.create_status_bar()

        # Load data
        self.load_data()

    def create_scrollable_canvas(self):
        """Create a scrollable canvas for the entire interface"""
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.bind_mousewheel()

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def bind_mousewheel(self):
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", on_mousewheel, add=True)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)

        bind_mousewheel_recursive(self.scrollable_frame)
        self.canvas.bind("<MouseWheel>", on_mousewheel)

    def setup_styles(self):
        """Configure custom styles for the application"""
        self.style = ttk.Style()

        try:
            self.style.theme_use('clam')
        except:
            pass

        self.bg_color = "#f0f0f0"
        self.fg_color = "#333333"
        self.accent_color = "#2c3e50"
        self.highlight_color = "#3498db"
        self.success_color = "#27ae60"

        self.style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#666666")
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=self.accent_color)
        self.style.configure("Success.TButton", font=("Segoe UI", 10), background=self.success_color)
        self.style.configure("Header.TLabelframe", font=("Segoe UI", 11, "bold"))
        self.style.configure("Header.TLabelframe.Label", font=("Segoe UI", 11, "bold"), foreground=self.accent_color)
        self.style.configure("Result.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.success_color)
        self.style.configure("Status.TLabel", font=("Segoe UI", 9))

        self.style.configure("Treeview",
                            font=("Segoe UI", 9),
                            rowheight=25,
                            background="#ffffff",
                            fieldbackground="#ffffff",
                            foreground="#333333")
        self.style.configure("Treeview.Heading",
                            font=("Segoe UI", 10, "bold"),
                            background=self.accent_color,
                            foreground="white")
        self.style.map("Treeview.Heading",
                      background=[("active", self.highlight_color)])

        self.style.configure("TNotebook.Tab",
                            font=("Segoe UI", 10),
                            padding=[10, 5])
        self.style.map("TNotebook.Tab",
                      background=[("selected", self.accent_color)],
                      foreground=[("selected", "white")])

    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 File", menu=file_menu)
        file_menu.add_command(label="📂 Load JSON...", command=self.load_data_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="💾 Export CSV", command=self.export_results_csv)
        file_menu.add_command(label="📄 Export XML", command=self.export_results_xml)
        file_menu.add_command(label="🔵 Export JSON", command=self.export_results_json)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self.root.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ View", menu=view_menu)
        view_menu.add_command(label="🌙 Dark Mode", command=self.toggle_theme)
        view_menu.add_command(label="☀️ Light Mode", command=self.toggle_theme)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Help", menu=help_menu)
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
        help_menu.add_command(label="📖 Shortcuts", command=self.show_shortcuts)

    def create_header(self):
        """Create header with title and description"""
        header_frame = tk.Frame(self.scrollable_frame, bg=self.bg_color, height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=(10, 5))
        header_frame.pack_propagate(False)

        title_label = ttk.Label(header_frame, text="🏛️ Packhum Greek Inscriptions Database",
                                style="Title.TLabel")
        title_label.pack(anchor=tk.W, pady=(10, 0))

        subtitle_label = ttk.Label(header_frame,
                                   text="Search and explore ancient Greek inscriptions from the Packard Humanities Institute Epigraphy Database",
                                   style="Subtitle.TLabel")
        subtitle_label.pack(anchor=tk.W)

    def create_search_frame(self):
        """Create search filters frame"""
        search_frame = ttk.LabelFrame(self.scrollable_frame, text="🔍 Search Filters",
                                      style="Header.TLabelframe", padding=15)
        search_frame.pack(fill=tk.X, padx=20, pady=10)

        notebook = ttk.Notebook(search_frame, height=330)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="📝 Basic Search")
        self.create_basic_tab(basic_frame)

        region_frame = ttk.Frame(notebook)
        notebook.add(region_frame, text="🌍 Region Search")
        self.create_region_tab(region_frame)

        date_frame = ttk.Frame(notebook)
        notebook.add(date_frame, text="📅 Date Search")
        self.create_date_tab(date_frame)

        button_frame = tk.Frame(search_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        self.search_button = tk.Button(button_frame, text="🔍 SEARCH DATABASE",
                                       command=self.search,
                                       bg=self.accent_color, fg="white",
                                       font=("Segoe UI", 11, "bold"),
                                       padx=20, pady=8,
                                       cursor="hand2",
                                       relief=tk.FLAT,
                                       activebackground=self.highlight_color,
                                       activeforeground="white")
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(button_frame, text="🗑 CLEAR ALL",
                                      command=self.clear_filters,
                                      bg="#95a5a6", fg="white",
                                      font=("Segoe UI", 10),
                                      padx=15, pady=8,
                                      cursor="hand2",
                                      relief=tk.FLAT,
                                      activebackground="#7f8c8d",
                                      activeforeground="white")
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.search_status = tk.Label(button_frame, text="● Ready",
                                      font=("Segoe UI", 9),
                                      fg=self.success_color,
                                      bg=self.bg_color)
        self.search_status.pack(side=tk.RIGHT, padx=10)

    def create_basic_tab(self, parent):
        """Create basic search tab"""
        frame = tk.Frame(parent, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Text search
        tk.Label(frame, text="Inscription text:",
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.text_var = StringVar()
        self.text_entry = ttk.Entry(frame, textvariable=self.text_var, width=70, font=("Segoe UI", 10))
        self.text_entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W)

        # Metadata search
        tk.Label(frame, text="Metadata (Publication):",
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.metadata_var = StringVar()
        self.metadata_entry = ttk.Entry(frame, textvariable=self.metadata_var, width=70, font=("Segoe UI", 10))
        self.metadata_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W)

        # ID search
        tk.Label(frame, text="Inscription ID (exact):",
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.id_var = StringVar()
        self.id_entry = ttk.Entry(frame, textvariable=self.id_var, width=20, font=("Segoe UI", 10))
        self.id_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # Book name search
        tk.Label(frame, text="Book name:",
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.book_name_entry = ttk.Entry(frame, textvariable=self.book_name_var, width=40, font=("Segoe UI", 10))
        self.book_name_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=3, sticky=tk.W)

        # Inscription number in book
        tk.Label(frame, text="Inscription number in book:",
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=4, column=0, sticky=tk.W, padx=5, pady=3)
        self.book_ref_entry = ttk.Entry(frame, textvariable=self.book_ref_var, width=40, font=("Segoe UI", 10))
        self.book_ref_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=3, sticky=tk.W)

        # Regex checkbox
        self.regex_check = tk.Checkbutton(
            frame, text="Use regex (applies to text & metadata; disables fuzzy ranking)",
            variable=self.use_regex_var,
            font=("Segoe UI", 9), bg=self.bg_color, activebackground=self.bg_color)
        self.regex_check.grid(row=5, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)

        # Ignore spaces checkbox
        self.ignore_signs_check = tk.Checkbutton(
            frame,
            text="Also ignore spaces — finds words split across line breaks or brackets (e.g. ε̣[ὐ-\nχήν])",
            variable=self.ignore_signs_var,
            font=("Segoe UI", 9), bg=self.bg_color, activebackground=self.bg_color)
        self.ignore_signs_check.grid(row=6, column=0, columnspan=4, sticky=tk.W, padx=5, pady=2)

        # Input mode
        tk.Label(frame, text="Input:",
                font=("Segoe UI", 9, "bold"), bg=self.bg_color).grid(row=7, column=0, sticky=tk.W, padx=5)
        input_frame = tk.Frame(frame, bg=self.bg_color)
        input_frame.grid(row=7, column=1, columnspan=3, sticky=tk.W, padx=5)
        for val, label in [('greek', 'Greek / Polytonic'), ('latin_translit', 'Latin transliteration'), ('latin', 'Latin script')]:
            tk.Radiobutton(input_frame, text=label, variable=self.input_mode_var, value=val,
                          font=("Segoe UI", 9), bg=self.bg_color,
                          activebackground=self.bg_color).pack(side=tk.LEFT, padx=8)

        # Hint
        tk.Label(frame,
                text=("💡  Editorial signs ([ ] { } ( ) · - …) always ignored · Results ranked: exact → all words → sequence → fuzzy"
                      " · Latin: th=θ  ph=φ  ch=χ  ps=ψ  ks=ξ  w=ω  h=η  x=ξ  y/u=υ  f=φ"
                      " · Metadata/Book: Roman↔Arabic expanded automatically (V↔5, X↔10 …)"),
                font=("Segoe UI", 8, "italic"), bg=self.bg_color, fg="#7f8c8d").grid(
                row=8, column=0, columnspan=4, sticky=tk.W, padx=5, pady=4)

    def create_region_tab(self, parent):
        """Create region search tab"""
        frame = tk.Frame(parent, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(frame, text="Region Main ID:",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_main_id_var = StringVar()
        self.region_main_id_entry = ttk.Entry(frame, textvariable=self.region_main_id_var, width=20, font=("Segoe UI", 10))
        self.region_main_id_entry.grid(row=0, column=1, padx=5, pady=8, sticky=tk.W)

        tk.Label(frame, text="Region Main Name:",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_main_var = StringVar()
        self.region_main_entry = ttk.Entry(frame, textvariable=self.region_main_var, width=50, font=("Segoe UI", 10))
        self.region_main_entry.grid(row=1, column=1, padx=5, pady=8, sticky=tk.W)

        tk.Label(frame, text="Region Sub ID:",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_sub_id_var = StringVar()
        self.region_sub_id_entry = ttk.Entry(frame, textvariable=self.region_sub_id_var, width=20, font=("Segoe UI", 10))
        self.region_sub_id_entry.grid(row=2, column=1, padx=5, pady=8, sticky=tk.W)

        tk.Label(frame, text="Region Sub Name:",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=3, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_sub_var = StringVar()
        self.region_sub_entry = ttk.Entry(frame, textvariable=self.region_sub_var, width=50, font=("Segoe UI", 10))
        self.region_sub_entry.grid(row=3, column=1, padx=5, pady=8, sticky=tk.W)

        tk.Label(frame, text="ℹ️ Note: If both ID and name are provided, ID takes precedence",
                font=("Segoe UI", 9, "italic"), bg=self.bg_color, fg="#e74c3c").grid(
                row=4, column=0, columnspan=2, pady=15, sticky=tk.W)

    def create_date_tab(self, parent):
        """Create date search tab"""
        frame = tk.Frame(parent, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(frame, text="Date String:",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        self.date_str_var = StringVar()
        self.date_str_entry = ttk.Entry(frame, textvariable=self.date_str_var, width=40, font=("Segoe UI", 10))
        self.date_str_entry.grid(row=0, column=1, padx=5, pady=8, sticky=tk.W)

        tk.Label(frame, text="Date Min (year BCE/CE):",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=8)
        self.date_min_var = StringVar()
        self.date_min_entry = ttk.Entry(frame, textvariable=self.date_min_var, width=15, font=("Segoe UI", 10))
        self.date_min_entry.grid(row=1, column=1, padx=5, pady=8, sticky=tk.W)
        tk.Label(frame, text="(e.g., -275 for 275 BCE)",
                font=("Segoe UI", 8), bg=self.bg_color, fg="#7f8c8d").grid(row=1, column=2, padx=5, sticky=tk.W)

        tk.Label(frame, text="Date Max (year BCE/CE):",
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.date_max_var = StringVar()
        self.date_max_entry = ttk.Entry(frame, textvariable=self.date_max_var, width=15, font=("Segoe UI", 10))
        self.date_max_entry.grid(row=2, column=1, padx=5, pady=8, sticky=tk.W)
        tk.Label(frame, text="(e.g., -226 for 226 BCE)",
                font=("Segoe UI", 8), bg=self.bg_color, fg="#7f8c8d").grid(row=2, column=2, padx=5, sticky=tk.W)

        self.date_circa_var = BooleanVar()
        self.date_circa_check = tk.Checkbutton(frame, text="📅 Circa Dating (uncertain date)",
                                               variable=self.date_circa_var,
                                               font=("Segoe UI", 10),
                                               bg=self.bg_color,
                                               activebackground=self.bg_color)
        self.date_circa_check.grid(row=3, column=0, columnspan=2, padx=5, pady=15, sticky=tk.W)

    def create_results_frame(self):
        """Create results display frame with all columns"""
        results_frame = ttk.LabelFrame(self.scrollable_frame, text="📊 Search Results",
                                       style="Header.TLabelframe", padding=15)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        count_frame = tk.Frame(results_frame, bg=self.bg_color)
        count_frame.pack(fill=tk.X, pady=(0, 10))

        self.results_count_label = tk.Label(count_frame, text="🔍 No results yet",
                                           font=("Segoe UI", 11, "bold"),
                                           fg=self.accent_color,
                                           bg=self.bg_color)
        self.results_count_label.pack(side=tk.LEFT)

        tk.Label(count_frame,
                 text="Click / Shift+click to select for export  ·  Double-click to view details",
                 font=("Segoe UI", 8, "italic"), fg="#7f8c8d", bg=self.bg_color
                 ).pack(side=tk.RIGHT, padx=10)

        tree_frame = tk.Frame(results_frame, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("ID", "Book name", "Inscription number in book", "Text", "Metadata", "Region main", "Region main ID",
                   "Region sub", "Region sub ID", "Date string", "Date min",
                   "Date max", "Date circa", "Score")

        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15,
                                 selectmode='extended')

        self.tree.heading("ID", text="🆔 ID")
        self.tree.heading("Book name", text="📖 Book name")
        self.tree.heading("Inscription number in book", text="📑 Inscription number in book ")
        self.tree.heading("Text", text="📜 Text")
        self.tree.heading("Metadata", text="📚 Metadata")
        self.tree.heading("Region main", text="🌍 Main Region")
        self.tree.heading("Region main ID", text="🔢 Main ID")
        self.tree.heading("Region sub", text="📍 Sub Region")
        self.tree.heading("Region sub ID", text="🔢 Sub ID")
        self.tree.heading("Date string", text="📅 Date String")
        self.tree.heading("Date min", text="⬇️ Min Year")
        self.tree.heading("Date max", text="⬆️ Max Year")
        self.tree.heading("Date circa", text="🔄 Circa")
        self.tree.heading("Score", text="📊 Score")

        self.tree.column("ID", width=60)
        self.tree.column("Book name", width=100)
        self.tree.column("Inscription number in book", width=150)
        self.tree.column("Text", width=280)
        self.tree.column("Metadata", width=230)
        self.tree.column("Region main", width=150)
        self.tree.column("Region main ID", width=100)
        self.tree.column("Region sub", width=150)
        self.tree.column("Region sub ID", width=100)
        self.tree.column("Date string", width=120)
        self.tree.column("Date min", width=80)
        self.tree.column("Date max", width=80)
        self.tree.column("Date circa", width=80)
        self.tree.column("Score", width=70)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind('<<TreeviewSelect>>', self.on_selection_change)
        self.tree.bind('<Double-1>', self.on_result_double_click)

        details_frame = ttk.LabelFrame(results_frame, text="📖 Entry Details",
                                      style="Header.TLabelframe", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.details_text = scrolledtext.ScrolledText(details_frame, height=10,
                                                      wrap=tk.WORD,
                                                      font=("Consolas", 10),
                                                      bg="#fef9e7",
                                                      fg="#2c3e50")
        self.details_text.pack(fill=tk.BOTH, expand=True)

    def create_export_frame(self):
        """Create export frame with filename entry and export buttons"""
        export_frame = ttk.LabelFrame(self.scrollable_frame, text="💾 Export Results",
                                      style="Header.TLabelframe", padding=15)
        export_frame.pack(fill=tk.X, padx=20, pady=10)

        left_frame = tk.Frame(export_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(left_frame, text="📄 Output Filename:",
                font=("Segoe UI", 10), bg=self.bg_color).pack(side=tk.LEFT, padx=5)

        self.output_filename_var = StringVar(value="search_results_packhum")
        self.filename_entry = ttk.Entry(left_frame, textvariable=self.output_filename_var,
                                        width=35, font=("Segoe UI", 10))
        self.filename_entry.pack(side=tk.LEFT, padx=5)

        self.format_frame = tk.Frame(left_frame, bg=self.bg_color)
        self.format_frame.pack(side=tk.LEFT, padx=10)

        self.csv_indicator = tk.Label(self.format_frame, text="CSV",
                                      font=("Segoe UI", 9, "bold"),
                                      bg="#27ae60", fg="white",
                                      padx=8, pady=2)
        self.csv_indicator.pack(side=tk.LEFT, padx=2)

        self.xml_indicator = tk.Label(self.format_frame, text="XML",
                                      font=("Segoe UI", 9, "bold"),
                                      bg="#3498db", fg="white",
                                      padx=8, pady=2)
        self.xml_indicator.pack(side=tk.LEFT, padx=2)

        self.json_indicator = tk.Label(self.format_frame, text="JSON",
                                       font=("Segoe UI", 9, "bold"),
                                       bg="#8e44ad", fg="white",
                                       padx=8, pady=2)
        self.json_indicator.pack(side=tk.LEFT, padx=2)

        right_frame = tk.Frame(export_frame, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT)

        self.csv_button = tk.Button(right_frame, text="💾 Export CSV",
                                    command=self.export_results_csv,
                                    bg="#27ae60", fg="white",
                                    font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=5,
                                    cursor="hand2",
                                    relief=tk.FLAT,
                                    activebackground="#219a52",
                                    activeforeground="white")
        self.csv_button.pack(side=tk.LEFT, padx=5)

        self.xml_button = tk.Button(right_frame, text="📄 Export XML",
                                    command=self.export_results_xml,
                                    bg="#3498db", fg="white",
                                    font=("Segoe UI", 10, "bold"),
                                    padx=15, pady=5,
                                    cursor="hand2",
                                    relief=tk.FLAT,
                                    activebackground="#2980b9",
                                    activeforeground="white")
        self.xml_button.pack(side=tk.LEFT, padx=5)

        self.json_button = tk.Button(right_frame, text="🔵 Export JSON",
                                     command=self.export_results_json,
                                     bg="#8e44ad", fg="white",
                                     font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=5,
                                     cursor="hand2",
                                     relief=tk.FLAT,
                                     activebackground="#7d3c98",
                                     activeforeground="white")
        self.json_button.pack(side=tk.LEFT, padx=5)

    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Label(self.root, text="● Ready",
                                   relief=tk.SUNKEN, anchor=tk.W,
                                   font=("Segoe UI", 9),
                                   bg="#ecf0f1", fg="#7f8c8d",
                                   padx=10, pady=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_theme(self):
        """Toggle between light and dark mode"""
        self.dark_mode = not self.dark_mode

        if self.dark_mode:
            self.bg_color = "#2c3e50"
            self.fg_color = "#ecf0f1"
            self.accent_color = "#3498db"
            self.style.theme_use('clam')
            self.status_bar.config(bg="#34495e", fg="#ecf0f1")
        else:
            self.bg_color = "#f0f0f0"
            self.fg_color = "#333333"
            self.accent_color = "#2c3e50"
            self.status_bar.config(bg="#ecf0f1", fg="#7f8c8d")

        messagebox.showinfo("Theme", f"Theme changed to {'Dark' if self.dark_mode else 'Light'} mode.\nRestart the application for full effect.")

    # ── text-normalisation & search helpers ──────────────────────────────────

    def _normalize_greek(self, text):
        """Strip diacritics/breathings and lowercase Greek text."""
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()

    def _latin_to_greek(self, text):
        """Convert Latin transliteration (scholarly) to stripped Greek.

        Digraph table  (processed first to avoid partial replacement):
          th→θ  ph→φ  ch→χ  ps→ψ  ks→ξ  rh→ρ
        Single-char table:
          a→α  b→β  g→γ  d→δ  e→ε  z→ζ  h→η  i→ι  j→ι  k→κ  l→λ
          m→μ  n→ν  o→ο  p→π  r→ρ  s→σ  t→τ  u→υ  v→υ  w→ω  x→ξ
          y→υ  f→φ
        """
        text = text.lower()
        for lat, grk in [('th', 'θ'), ('ph', 'φ'), ('ch', 'χ'), ('ps', 'ψ'),
                         ('ks', 'ξ'), ('rh', 'ρ')]:
            text = text.replace(lat, grk)
        for lat, grk in [('a', 'α'), ('b', 'β'), ('g', 'γ'), ('d', 'δ'), ('e', 'ε'),
                         ('z', 'ζ'), ('h', 'η'), ('i', 'ι'), ('j', 'ι'), ('k', 'κ'),
                         ('l', 'λ'), ('m', 'μ'), ('n', 'ν'), ('o', 'ο'), ('p', 'π'),
                         ('r', 'ρ'), ('s', 'σ'), ('t', 'τ'), ('u', 'υ'), ('v', 'υ'),
                         ('w', 'ω'), ('x', 'ξ'), ('y', 'υ'), ('f', 'φ')]:
            text = text.replace(lat, grk)
        return text

    def _is_latin_input(self, text):
        """Return True if the majority of letter characters are ASCII (Latin script)."""
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return False
        return sum(1 for c in letters if ord(c) < 128) / len(letters) > 0.5

    def _normalize_query(self, query):
        """Normalise a query string according to the current input-mode setting.

        Applies the same sign-stripping used on the DB cache: bracket chars
        removed, diacritics stripped, then all non-letter non-space chars dropped
        and whitespace collapsed.  This matches the default search mode.
        """
        clean = self._bracket_re.sub('', query)
        mode = self.input_mode_var.get()
        if mode == 'latin_translit':
            norm = self._latin_to_greek(clean)
        else:  # 'greek' — Latin mode never calls this function
            norm = self._normalize_greek(clean)
        return ' '.join(''.join(c for c in norm if c.isalpha() or c.isspace()).split())

    _bracket_re = re.compile(r'[\[\](){}]')
    _latin_letters_re = re.compile(r'[a-z]+')

    def _precompute_normalized(self):
        """Build per-entry text caches.

        normalized_text_cache  – bracket chars + diacritics + editorial signs
                                  (hyphens, dots, digits, …) removed; spaces kept.
                                  This is the default search target.
        normalized_words_cache – word list derived from the above.
        bare_text_cache        – same but spaces also removed; used when
                                  "Ignore spaces" is checked.
        """
        self.normalized_text_cache = []
        self.normalized_words_cache = []
        self.bare_text_cache = []
        self.latin_text_cache = []
        self.bare_latin_text_cache = []
        for entry in self.data:
            clean = self._bracket_re.sub('', entry.get('text', ''))
            norm = self._normalize_greek(clean)
            # Greek cache: strip non-letter non-space chars, collapse whitespace
            signs_stripped = ' '.join(
                ''.join(c for c in norm if c.isalpha() or c.isspace()).split()
            )
            self.normalized_text_cache.append(signs_stripped)
            self.normalized_words_cache.append(signs_stripped.split())
            # Bare Greek: spaces also removed
            self.bare_text_cache.append(signs_stripped.replace(' ', ''))
            # Latin cache: ASCII letter sequences from bracket-stripped raw text
            latin = ' '.join(self._latin_letters_re.findall(clean.lower()))
            self.latin_text_cache.append(latin)
            self.bare_latin_text_cache.append(latin.replace(' ', ''))

    def _word_sequence_match(self, query_words, text_words):
        """Return True if every query word appears in text_words in the given order.

        Words between query words are allowed (non-contiguous match).
        Example: ['στοματων', 'επει'] matches ['στοματων', 'ομως', 'επει'].
        """
        if not query_words:
            return False
        qi = 0
        for tw in text_words:
            if tw == query_words[qi]:
                qi += 1
                if qi == len(query_words):
                    return True
        return False

    def _levenshtein(self, s1, s2, cutoff=3):
        """Character edit distance with early exit when result would exceed cutoff."""
        if abs(len(s1) - len(s2)) > cutoff:
            return cutoff + 1
        m, n = len(s1), len(s2)
        dp = list(range(n + 1))
        for i, c1 in enumerate(s1):
            prev, dp[0] = dp[0], i + 1
            for j, c2 in enumerate(s2):
                prev, dp[j + 1] = dp[j + 1], min(
                    prev + (0 if c1 == c2 else 1),
                    dp[j + 1] + 1,
                    dp[j] + 1
                )
            if min(dp) > cutoff:
                return cutoff + 1
        return dp[n]

    def _auto_score(self, query_words, db_text, db_words):
        """Score one entry against the query; returns (float, label) or None.

        Levels, ranked best-first:
          4  exact substring (all query words consecutive in text)
          3  all words present, any order
          2  words appear in order with gaps allowed (sequence)
          0–1  fuzzy: fraction of words matched within 1 edit
        """
        if not query_words:
            return None

        query_str = ' '.join(query_words)
        if query_str in db_text:
            return 4.0, 'exact'

        db_set = set(db_words)
        if all(w in db_set for w in query_words):
            return 3.0, 'all words'

        if self._word_sequence_match(query_words, db_words):
            return 2.0, 'sequence'

        matched = 0
        for qw in query_words:
            if len(qw) <= 2:
                if qw in db_set:
                    matched += 1
            elif qw in db_set:
                matched += 1
            else:
                candidates = [tw for tw in db_words if abs(len(tw) - len(qw)) <= 1]
                if any(self._levenshtein(qw, tw, 1) <= 1 for tw in candidates):
                    matched += 1
        if matched == 0:
            return None
        pct = int(100 * matched / len(query_words))
        return matched / len(query_words), f'fuzzy {pct}%'

    def _build_metadata_pattern(self, query):
        """Build a regex pattern for metadata/book-name search.

        Each word token that is a valid Roman numeral (I–XXX) is expanded to
        match either the Roman form or its Arabic equivalent as a whole word,
        so searching 'V' will not hit 'VI' or 'VII'.  Arabic tokens 1–30 are
        similarly expanded to also match their Roman form.
        """
        result = []
        pos = 0
        for m in re.finditer(r'[A-Za-z]+|\d+', query):
            result.append(re.escape(query[pos:m.start()]))
            token = m.group(0)
            upper = token.upper()
            if re.match(r'^[IVXLCDM]+$', upper) and upper in _ROMAN_TO_INT:
                arabic = str(_ROMAN_TO_INT[upper])
                result.append(r'(?:\b' + re.escape(upper) + r'\b|\b' + arabic + r'\b)')
            elif token.isdigit():
                num = int(token)
                if num in _INT_TO_ROMAN:
                    roman = _INT_TO_ROMAN[num]
                    result.append(r'(?:\b' + roman + r'\b|\b' + re.escape(token) + r'\b)')
                else:
                    result.append(re.escape(token))
            else:
                result.append(re.escape(token))
            pos = m.end()
        result.append(re.escape(query[pos:]))
        return ''.join(result)

    # ── data loading ──────────────────────────────────────────────────────────

    def load_data(self, filename="C:\\PATH\\TO\\packhum.json"):
        """Load JSON data in background thread"""
        self.status_bar.config(text=f"⏳ Loading {filename}...")
        self.search_button.config(state=tk.DISABLED)
        self.search_status.config(text="● Loading...", fg="#f39c12")

        def load():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                self.status_bar and self.root.after(
                    0, lambda: self.status_bar.config(text="⏳ Building search index…"))
                self._precompute_normalized()
                self.root.after(0, self.on_data_loaded, filename)
            except Exception as e:
                self.root.after(0, self.on_load_error, str(e))

        thread = threading.Thread(target=load)
        thread.daemon = True
        thread.start()

    def on_data_loaded(self, filename):
        """Callback when data is loaded"""
        self.status_bar.config(text=f"✅ Loaded {len(self.data):,} entries from {filename}")
        self.search_button.config(state=tk.NORMAL)
        self.search_status.config(text="● Ready", fg=self.success_color)
        messagebox.showinfo("Success", f"✅ Successfully loaded {len(self.data):,} inscriptions!\n\nDatabase loaded and ready for searching.")

    def on_load_error(self, error):
        """Callback when load fails"""
        self.status_bar.config(text=f"❌ Error loading file")
        self.search_button.config(state=tk.NORMAL)
        self.search_status.config(text="● Error", fg="#e74c3c")
        messagebox.showerror("Error", f"❌ Failed to load JSON file:\n{error}")

    def load_data_dialog(self):
        """Open file dialog to load JSON"""
        filename = filedialog.askopenfilename(
            title="Select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.load_data(filename)

    # ── search ────────────────────────────────────────────────────────────────

    def search(self):
        """Perform search based on filters"""
        if not self.data:
            messagebox.showwarning("Warning", "⚠️ Please load data first")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.details_text.delete(1.0, tk.END)

        filters = {}

        if self.text_var.get().strip():
            filters['text'] = self.text_var.get().strip()
        if self.metadata_var.get().strip():
            filters['metadata'] = self.metadata_var.get().strip()
        if self.id_var.get().strip():
            filters['id'] = self.id_var.get().strip()

        if self.book_name_var.get().strip():
            filters['book_name'] = self.book_name_var.get().strip()
        if self.book_ref_var.get().strip():
            filters['book_ref'] = self.book_ref_var.get().strip()

        filters['_regex'] = self.use_regex_var.get()
        filters['_ignore_signs'] = self.ignore_signs_var.get()
        filters['_input_mode'] = self.input_mode_var.get()

        if self.region_main_id_var.get().strip():
            filters['region_main_id'] = self.region_main_id_var.get().strip()
        elif self.region_main_var.get().strip():
            filters['region_main'] = self.region_main_var.get().strip()

        if self.region_sub_id_var.get().strip():
            filters['region_sub_id'] = self.region_sub_id_var.get().strip()
        elif self.region_sub_var.get().strip():
            filters['region_sub'] = self.region_sub_var.get().strip()

        if self.date_str_var.get().strip():
            filters['date_str'] = self.date_str_var.get().strip()
        if self.date_min_var.get().strip():
            filters['date_min'] = self.date_min_var.get().strip()
        if self.date_max_var.get().strip():
            filters['date_max'] = self.date_max_var.get().strip()
        if self.date_circa_var.get():
            filters['date_circa'] = True

        if not any(k not in ('_regex', '_ignore_signs', '_input_mode') for k in filters):
            messagebox.showwarning("Warning", "⚠️ Please enter at least one search filter")
            return

        self.status_bar.config(text="🔍 Searching...")
        self.search_button.config(state=tk.DISABLED)
        self.search_status.config(text="● Searching...", fg="#f39c12")

        def search_thread():
            results = self.search_entries(filters)
            self.root.after(0, self.display_results, results)

        thread = threading.Thread(target=search_thread)
        thread.daemon = True
        thread.start()

    def search_entries(self, filters):
        """Search entries; returns list of (entry, score_label) tuples, ranked best-first."""
        use_regex = filters.pop('_regex', False)
        ignore_signs = filters.pop('_ignore_signs', False)
        input_mode = filters.pop('_input_mode', 'greek')
        raw_text = filters.get('text', '')

        # Split filters into categories
        text_type = ('metadata', 'book_name', 'book_ref')
        text_filters = {k: v for k, v in filters.items() if k in text_type}
        other_filters = {k: v for k, v in filters.items() if k not in text_type and k != 'text'}

        text_query = None      # for Greek / Greek-transliterated mode
        latin_query = None     # for Latin script mode
        query_words = None
        if raw_text:
            if use_regex:
                text_query = raw_text  # used as-is against raw polytonic text
            elif input_mode == 'latin':
                # Latin mode: match raw ASCII letters only
                latin_query = ' '.join(self._latin_letters_re.findall(raw_text.lower()))
            else:
                text_query = self._normalize_query(raw_text)
                query_words = text_query.split()

        scored = []  # (score, entry, label)

        for i, entry in enumerate(self.data):
            skip = False

            # Exact / typed filters (ID, date_circa, numeric dates, regions)
            for field, search_value in other_filters.items():
                field_value = entry.get(field, '')
                if field == 'id':
                    if str(field_value) != str(search_value):
                        skip = True; break
                elif field == 'date_circa':
                    if field_value != search_value:
                        skip = True; break
                else:
                    if str(search_value).lower() not in str(field_value).lower():
                        skip = True; break
            if skip:
                continue

            # Text-type filters: metadata, book_name, book_ref
            for field, search_value in text_filters.items():
                field_value = str(entry.get(field, ''))
                if use_regex:
                    try:
                        if not re.search(search_value, field_value, re.IGNORECASE):
                            skip = True; break
                    except re.error:
                        skip = True; break
                elif field in ('metadata', 'book_name'):
                    pat = self._build_metadata_pattern(search_value)
                    if not re.search(pat, field_value, re.IGNORECASE):
                        skip = True; break
                else:  # book_ref: plain substring
                    if search_value.lower() not in field_value.lower():
                        skip = True; break
            if skip:
                continue

            # Inscription text filter
            if text_query is None and latin_query is None:
                scored.append((5.0, entry, '—'))
                continue

            if use_regex:
                try:
                    if re.search(text_query, entry.get('text', ''), re.IGNORECASE):
                        scored.append((4.0, entry, 'regex'))
                except re.error:
                    pass
                continue

            # ── Latin script mode ────────────────────────────────────────────
            if latin_query is not None:
                if ignore_signs:
                    bare_lq = latin_query.replace(' ', '')
                    if bare_lq:
                        bare_db = self.bare_latin_text_cache[i] if self.bare_latin_text_cache is not None else self.latin_text_cache[i].replace(' ', '')
                        if bare_lq in bare_db:
                            scored.append((4.0, entry, 'latin bare'))
                            continue
                db_latin = self.latin_text_cache[i] if self.latin_text_cache is not None else ' '.join(self._latin_letters_re.findall(self._bracket_re.sub('', entry.get('text', '')).lower()))
                lq_words = latin_query.split()
                result = self._auto_score(lq_words, db_latin, db_latin.split())
                if result is not None:
                    score, label = result
                    scored.append((score, entry, 'latin:' + label))
                continue

            # ── Greek / transliteration mode ─────────────────────────────────
            if self.normalized_text_cache is not None:
                db_text = self.normalized_text_cache[i]
                db_words = self.normalized_words_cache[i]
            else:
                clean = self._bracket_re.sub('', entry.get('text', ''))
                db_text = self._normalize_greek(clean)
                db_words = db_text.split()

            # Bare-exact tier: catches words split by brackets or hyphens.
            if ignore_signs:
                bare_query = ''.join(c for c in text_query if c.isalpha())
                if bare_query:
                    if self.bare_text_cache is not None:
                        bare_db = self.bare_text_cache[i]
                    else:
                        bare_db = ''.join(c for c in db_text if c.isalpha())
                    if bare_query in bare_db:
                        scored.append((4.0, entry, 'bare exact'))
                        continue

            result = self._auto_score(query_words, db_text, db_words)
            if result is not None:
                score, label = result
                scored.append((score, entry, label))

        scored.sort(key=lambda x: -x[0])
        return [(e, label) for _, e, label in scored]

    def display_results(self, results):
        """Display search results in treeview. results = [(entry, score_label), ...]"""
        self.current_results = [r[0] for r in results]
        self._result_scores = {str(r[0].get('id')): r[1] for r in results}

        result_icon = "🔍" if len(results) == 0 else "✅" if len(results) < 1000 else "📊"
        self.results_count_label.config(
            text=f"{result_icon} Found {len(results):,} matching entries")
        self.status_bar.config(text=f"✅ Search complete - {len(results):,} results found")
        self.search_button.config(state=tk.NORMAL)
        self.search_status.config(text="● Ready", fg=self.success_color)

        for entry, score in results[:2000]:
            text_val = entry.get('text', 'N/A')
            meta_val = entry.get('metadata', 'N/A')
            self.tree.insert("", tk.END, values=(
                entry.get('id', 'N/A'),
                entry.get('book_name', 'N/A'),
                entry.get('book_ref', 'N/A'),
                text_val[:200] + "…" if len(text_val) > 200 else text_val,
                meta_val[:150] + "…" if len(meta_val) > 150 else meta_val,
                entry.get('region_main', 'N/A'),
                entry.get('region_main_id', 'N/A'),
                entry.get('region_sub', 'N/A'),
                entry.get('region_sub_id', 'N/A'),
                entry.get('date_str', 'N/A'),
                entry.get('date_min', 'N/A'),
                entry.get('date_max', 'N/A'),
                entry.get('date_circa', 'N/A'),
                score,
            ), tags=(entry.get('id', ''),))

        if len(results) > 2000:
            self.status_bar.config(
                text=f"⚠️ Showing first 2000 of {len(results):,} results (use export for all)")

    def on_selection_change(self, event):
        """Update status bar with selection count."""
        n = len(self.tree.selection())
        if n == 1:
            self.status_bar.config(
                text="1 row selected · double-click to view details · Export saves selection")
        elif n > 1:
            self.status_bar.config(
                text=f"{n} rows selected · Export saves selection")

    def on_result_double_click(self, event):
        """Show details for the double-clicked row."""
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        values = self.tree.item(iid)['values']
        if not values:
            return
        selected_id = str(values[0])
        for result in self.current_results:
            if str(result.get('id')) == selected_id:
                self.display_entry_details(result)
                break

    def _get_selected_entries(self):
        """Return selected rows, or all current_results if nothing is selected."""
        sel = self.tree.selection()
        if not sel:
            return self.current_results
        selected_ids = {str(self.tree.item(iid)['values'][0]) for iid in sel}
        return [e for e in self.current_results if str(e.get('id')) in selected_ids]

    def display_entry_details(self, entry):
        """Display full entry details in text area"""
        self.details_text.delete(1.0, tk.END)

        score = self._result_scores.get(str(entry.get('id')), '')
        score_suffix = f"  [match: {score}]" if score and score not in ('—', '✓') else ""

        details = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              INSCRIPTION DETAILS                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ID: {str(str(entry.get('id', 'N/A')) + score_suffix).ljust(67)}║
║ Book: {str(entry.get('book_name', 'N/A'))[:28].ljust(28)}  Ref: {str(entry.get('book_ref', ''))[:33].ljust(33)}║
╠══════════════════════════════════════════════════════════════════════════════╣
║ TEXT:                                                                        ║
║ {self.format_text(entry.get('text', 'N/A'), 70)}║
╠══════════════════════════════════════════════════════════════════════════════╣
║ METADATA:                                                                    ║
║ {self.format_text(entry.get('metadata', 'N/A'), 70)}║
╠══════════════════════════════════════════════════════════════════════════════╣
║ REGION INFORMATION:                                                          ║
║   Main Region: {str(entry.get('region_main', 'N/A'))[:40].ljust(40)} (ID: {entry.get('region_main_id', 'N/A')})║
║   Sub Region:  {str(entry.get('region_sub', 'N/A'))[:40].ljust(40)} (ID: {entry.get('region_sub_id', 'N/A')})║
╠══════════════════════════════════════════════════════════════════════════════╣
║ DATE INFORMATION:                                                            ║
║   String: {str(entry.get('date_str', 'N/A'))[:50].ljust(50)}║
║   Min: {str(entry.get('date_min', 'N/A')).ljust(20)} Max: {str(entry.get('date_max', 'N/A')).ljust(20)} Circa: {str(entry.get('date_circa', 'N/A')).ljust(10)}║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        self.details_text.insert(1.0, details)

    def format_text(self, text, width):
        """Format text for display in the details box"""
        if not text or text == 'N/A':
            return "N/A".ljust(width)

        lines = []
        words = str(text).split()
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                current_line = (current_line + " " + word).lstrip() if current_line else word
            else:
                lines.append(current_line.ljust(width))
                current_line = word

        if current_line:
            lines.append(current_line.ljust(width))

        return "\n║ ".join(lines)

    def export_results_csv(self):
        """Export selected rows (or all results) to CSV."""
        entries = self._get_selected_entries()
        if not entries:
            messagebox.showwarning("Warning", "⚠️ No results to export")
            return

        base_filename = self.output_filename_var.get().strip() or "search_results_packhum"
        filename = filedialog.asksaveasfilename(
            title="Save CSV file",
            initialfile=f"{base_filename}.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            try:
                fieldnames = ['id', 'book_name', 'book_ref', 'text', 'metadata', 'region_main', 'region_main_id',
                             'region_sub', 'region_sub_id', 'date_str', 'date_min',
                             'date_max', 'date_circa']

                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(entries)

                messagebox.showinfo("Success", f"✅ Exported {len(entries):,} entries to {filename}")
                self.status_bar.config(text=f"✅ Exported {len(entries):,} entries to CSV")
            except Exception as e:
                messagebox.showerror("Error", f"❌ Failed to export: {str(e)}")

    def export_results_xml(self):
        """Export selected rows (or all results) to XML."""
        entries = self._get_selected_entries()
        if not entries:
            messagebox.showwarning("Warning", "⚠️ No results to export")
            return

        base_filename = self.output_filename_var.get().strip() or "search_results_packhum"
        filename = filedialog.asksaveasfilename(
            title="Save XML file",
            initialfile=f"{base_filename}.xml",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )

        if filename:
            try:
                root = ET.Element("search_results")
                root.set("total_results", str(len(entries)))
                root.set("export_date", datetime.now().isoformat())

                for entry in entries:
                    entry_elem = ET.SubElement(root, "entry")
                    for key, value in entry.items():
                        field_elem = ET.SubElement(entry_elem, key)
                        if value is not None:
                            field_elem.text = str(value)
                        else:
                            field_elem.set("nil", "true")

                xml_str = ET.tostring(root, encoding='unicode')
                dom = minidom.parseString(xml_str)
                pretty_xml = dom.toprettyxml(indent="  ")

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(pretty_xml)

                messagebox.showinfo("Success", f"✅ Exported {len(entries):,} entries to {filename}")
                self.status_bar.config(text=f"✅ Exported {len(entries):,} entries to XML")
            except Exception as e:
                messagebox.showerror("Error", f"❌ Failed to export XML: {str(e)}")

    def export_results_json(self):
        """Export selected rows (or all results) to JSON, matching input json format."""
        entries = self._get_selected_entries()
        if not entries:
            messagebox.showwarning("Warning", "⚠️ No results to export")
            return

        base_filename = self.output_filename_var.get().strip() or "search_results_packhum"
        filename = filedialog.asksaveasfilename(
            title="Save JSON file",
            initialfile=f"{base_filename}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Success", f"✅ Exported {len(entries):,} entries to {filename}")
                self.status_bar.config(text=f"✅ Exported {len(entries):,} entries to JSON")
            except Exception as e:
                messagebox.showerror("Error", f"❌ Failed to export JSON: {str(e)}")

    def clear_filters(self):
        """Clear all filter fields"""
        self.text_var.set("")
        self.metadata_var.set("")
        self.id_var.set("")
        self.book_name_var.set("")
        self.book_ref_var.set("")
        self.use_regex_var.set(False)
        self.region_main_id_var.set("")
        self.region_main_var.set("")
        self.region_sub_id_var.set("")
        self.region_sub_var.set("")
        self.date_str_var.set("")
        self.date_min_var.set("")
        self.date_max_var.set("")
        self.date_circa_var.set(False)

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.details_text.delete(1.0, tk.END)
        self.results_count_label.config(text="🔍 No results yet")
        self.current_results = []
        self._result_scores = {}
        self.status_bar.config(text="🗑 Filters cleared")
        self.search_status.config(text="● Ready", fg=self.success_color)

    def show_about(self):
        """Show about dialog"""
        about_text = """🏛️ Veatriki — PHI Greek Inscriptions search tool
by Beatrice "Bice" Pavesi (pavesi@chalmers.se)
═══════════════════════════════════════════════

A graphical interface for searching the Packard Humanities
Institute (PHI) database of Greek inscriptions.

✨ Features:
• Search by inscription ID, text, metadata, book name/number
• Filter by region (name or ID) and date
• Regex support in text and metadata search bars
• Ignore editorial signs ([ ] { } ( ) · - …) during text search
• Export results to CSV, XML, or JSON
• Detailed inscription viewer with match score

🔍 Text Search Ranking (Greek & transliteration modes):
• Exact substring   – score 4  (highest)
• All words present – score 3
• Word sequence     – score 2
• Fuzzy             – score 0–1

🔤 Input Modes:
• Greek / Polytonic  – diacritics stripped before matching;
                       matches Greek-script inscriptions only
• Latin translit.    – th=θ  ph=φ  ch=χ  ps=ψ  ks=ξ  rh=ρ
                       w=ω  h=η  x=ξ  y=υ;
                       matches Greek-script inscriptions only
• Latin script       – matches ASCII letter sequences;
                       matches Latin-script inscriptions only

📊 Data source:
packhum.json — all entries from epigraphy.packhum.org

🔧 Technical:
• Built with Python 3 and tkinter
• Background threading for smooth UI during load and search

Version 2.2
"""
        messagebox.showinfo("About Veatriki", about_text)

    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts_text = """⌨️ Keyboard Shortcuts
═══════════════════════

🔍 Search:           Enter (when in search field)
🗑 Clear All:        Ctrl+C
💾 Export CSV:       Ctrl+E
📄 Export XML:       Ctrl+X
📂 Load JSON:        Ctrl+O
❓ Help:             F1
🚪 Exit:             Ctrl+Q

💡 Tips:
• Accents and diacritics are stripped automatically (Greek modes)
• "Ignore editorial signs" strips [ ] { } ( ) · - and digits from
  both query and database text before matching — useful for words
  split across brackets or line breaks
• "Also ignore spaces" additionally removes spaces, so a bare
  letter sequence matches even across line endings
• Use regex mode for full regular-expression matching in the
  text and metadata fields (Python re syntax)
• Latin translit.: th=θ  ph=φ  ch=χ  ps=ψ  ks=ξ  rh=ρ  w=ω
• Region ID takes precedence over region name if both are filled
• BCE years are negative numbers (e.g., -275)
• JSON export preserves the full entry format of packhum.json,
  so results can be fed back as input for iterative searches
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)


def main():
    root = tk.Tk()
    app = PackhumSearchGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
