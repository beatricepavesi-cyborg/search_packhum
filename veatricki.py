#!/usr/bin/env python3
"""
search_packhum_gui.py - Beautiful GUI interface for searching iphi.json using tkinter
"""

import json
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from tkinter import BooleanVar, StringVar, IntVar
from collections import defaultdict
import threading
from pathlib import Path
from datetime import datetime

class PackhumSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🏛️ Packhum Greek Inscriptions Search")
        self.root.geometry("1400x900")
        
        # Set application icon (optional - if you have an icon file)
        # self.root.iconbitmap("icon.ico")
        
        # Configure style
        self.setup_styles()
        
        # Data storage
        self.data = None
        self.current_results = []
        self.dark_mode = False
        
        # Create GUI
        self.create_menu()
        self.create_header()
        self.create_search_frame()
        self.create_results_frame()
        self.create_export_frame()
        self.create_status_bar()
        
        # Load data
        self.load_data()
    
    def setup_styles(self):
        """Configure custom styles for the application"""
        self.style = ttk.Style()
        
        # Available themes: 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'
        try:
            self.style.theme_use('clam')
        except:
            pass
        
        # Configure colors
        self.bg_color = "#f0f0f0"
        self.fg_color = "#333333"
        self.accent_color = "#2c3e50"
        self.highlight_color = "#3498db"
        self.success_color = "#27ae60"
        
        # Configure styles
        self.style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.accent_color)
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#666666")
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=self.accent_color)
        self.style.configure("Success.TButton", font=("Segoe UI", 10), background=self.success_color)
        self.style.configure("Header.TLabelframe", font=("Segoe UI", 11, "bold"))
        self.style.configure("Header.TLabelframe.Label", font=("Segoe UI", 11, "bold"), foreground=self.accent_color)
        self.style.configure("Result.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.success_color)
        self.style.configure("Status.TLabel", font=("Segoe UI", 9))
        
        # Configure Treeview
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
        
        # Configure Tab style
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
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 File", menu=file_menu)
        file_menu.add_command(label="📂 Load JSON...", command=self.load_data_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="💾 Export CSV", command=self.export_results_csv)
        file_menu.add_command(label="📄 Export XML", command=self.export_results_xml)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ View", menu=view_menu)
        view_menu.add_command(label="🌙 Dark Mode", command=self.toggle_theme)
        view_menu.add_command(label="☀️ Light Mode", command=self.toggle_theme)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Help", menu=help_menu)
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
        help_menu.add_command(label="📖 Shortcuts", command=self.show_shortcuts)
    
    def create_header(self):
        """Create header with title and description"""
        header_frame = tk.Frame(self.root, bg=self.bg_color, height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=(10, 5))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = ttk.Label(header_frame, text="🏛️ Packhum Greek Inscriptions Database", 
                                style="Title.TLabel")
        title_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame, 
                                   text="Search and explore ancient Greek inscriptions from the Packhum Epigraphy Database",
                                   style="Subtitle.TLabel")
        subtitle_label.pack(anchor=tk.W)
    
    def create_search_frame(self):
        """Create search filters frame"""
        search_frame = ttk.LabelFrame(self.root, text="🔍 Search Filters", 
                                      style="Header.TLabelframe", padding=15)
        search_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(search_frame, height=180)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Basic Search
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="📝 Basic Search")
        self.create_basic_tab(basic_frame)
        
        # Tab 2: Region Search
        region_frame = ttk.Frame(notebook)
        notebook.add(region_frame, text="🌍 Region Search")
        self.create_region_tab(region_frame)
        
        # Tab 3: Date Search
        date_frame = ttk.Frame(notebook)
        notebook.add(date_frame, text="📅 Date Search")
        self.create_date_tab(date_frame)
        
        # Search button frame
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
        
        # Status indicator
        self.search_status = tk.Label(button_frame, text="● Ready", 
                                      font=("Segoe UI", 9),
                                      fg=self.success_color,
                                      bg=self.bg_color)
        self.search_status.pack(side=tk.RIGHT, padx=10)
    
    def create_basic_tab(self, parent):
        """Create basic search tab"""
        # Use tk.Frame instead of ttk.Frame for bg color support
        frame = tk.Frame(parent, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Text search
        tk.Label(frame, text="Greek Inscription Text:", 
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        self.text_var = StringVar()
        self.text_entry = ttk.Entry(frame, textvariable=self.text_var, width=70, font=("Segoe UI", 10))
        self.text_entry.grid(row=0, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Metadata search
        tk.Label(frame, text="Metadata (Publication):", 
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=1, column=0, sticky=tk.W, padx=5, pady=8)
        self.metadata_var = StringVar()
        self.metadata_entry = ttk.Entry(frame, textvariable=self.metadata_var, width=70, font=("Segoe UI", 10))
        self.metadata_entry.grid(row=1, column=1, padx=5, pady=8, sticky=tk.W)
        
        # ID search
        tk.Label(frame, text="Inscription ID (exact):", 
                font=("Segoe UI", 10), bg=self.bg_color, anchor=tk.W).grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.id_var = StringVar()
        self.id_entry = ttk.Entry(frame, textvariable=self.id_var, width=20, font=("Segoe UI", 10))
        self.id_entry.grid(row=2, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Hint
        hint_label = tk.Label(frame, text="💡 Tip: Use partial words - search is case-insensitive", 
                             font=("Segoe UI", 8, "italic"), bg=self.bg_color, fg="#7f8c8d")
        hint_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)
    
    def create_region_tab(self, parent):
        """Create region search tab"""
        frame = tk.Frame(parent, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Region Main ID
        tk.Label(frame, text="Region Main ID:", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_main_id_var = StringVar()
        self.region_main_id_entry = ttk.Entry(frame, textvariable=self.region_main_id_var, width=20, font=("Segoe UI", 10))
        self.region_main_id_entry.grid(row=0, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Region Main Name
        tk.Label(frame, text="Region Main Name:", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_main_var = StringVar()
        self.region_main_entry = ttk.Entry(frame, textvariable=self.region_main_var, width=50, font=("Segoe UI", 10))
        self.region_main_entry.grid(row=1, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Region Sub ID
        tk.Label(frame, text="Region Sub ID:", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_sub_id_var = StringVar()
        self.region_sub_id_entry = ttk.Entry(frame, textvariable=self.region_sub_id_var, width=20, font=("Segoe UI", 10))
        self.region_sub_id_entry.grid(row=2, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Region Sub Name
        tk.Label(frame, text="Region Sub Name:", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=3, column=0, sticky=tk.W, padx=5, pady=8)
        self.region_sub_var = StringVar()
        self.region_sub_entry = ttk.Entry(frame, textvariable=self.region_sub_var, width=50, font=("Segoe UI", 10))
        self.region_sub_entry.grid(row=3, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Precedence info
        info_label = tk.Label(frame, text="ℹ️ Note: If both ID and name are provided, ID takes precedence", 
                             font=("Segoe UI", 9, "italic"), bg=self.bg_color, fg="#e74c3c")
        info_label.grid(row=4, column=0, columnspan=2, pady=15, sticky=tk.W)
    
    def create_date_tab(self, parent):
        """Create date search tab"""
        frame = tk.Frame(parent, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Date string
        tk.Label(frame, text="Date String:", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=0, column=0, sticky=tk.W, padx=5, pady=8)
        self.date_str_var = StringVar()
        self.date_str_entry = ttk.Entry(frame, textvariable=self.date_str_var, width=40, font=("Segoe UI", 10))
        self.date_str_entry.grid(row=0, column=1, padx=5, pady=8, sticky=tk.W)
        
        # Date min
        tk.Label(frame, text="Date Min (year BCE/CE):", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=1, column=0, sticky=tk.W, padx=5, pady=8)
        self.date_min_var = StringVar()
        self.date_min_entry = ttk.Entry(frame, textvariable=self.date_min_var, width=15, font=("Segoe UI", 10))
        self.date_min_entry.grid(row=1, column=1, padx=5, pady=8, sticky=tk.W)
        tk.Label(frame, text="(e.g., -275 for 275 BCE)", 
                font=("Segoe UI", 8), bg=self.bg_color, fg="#7f8c8d").grid(row=1, column=2, padx=5, sticky=tk.W)
        
        # Date max
        tk.Label(frame, text="Date Max (year BCE/CE):", 
                font=("Segoe UI", 10), bg=self.bg_color).grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.date_max_var = StringVar()
        self.date_max_entry = ttk.Entry(frame, textvariable=self.date_max_var, width=15, font=("Segoe UI", 10))
        self.date_max_entry.grid(row=2, column=1, padx=5, pady=8, sticky=tk.W)
        tk.Label(frame, text="(e.g., -226 for 226 BCE)", 
                font=("Segoe UI", 8), bg=self.bg_color, fg="#7f8c8d").grid(row=2, column=2, padx=5, sticky=tk.W)
        
        # Date circa
        self.date_circa_var = BooleanVar()
        self.date_circa_check = tk.Checkbutton(frame, text="📅 Circa Dating (uncertain date)", 
                                               variable=self.date_circa_var,
                                               font=("Segoe UI", 10),
                                               bg=self.bg_color,
                                               activebackground=self.bg_color)
        self.date_circa_check.grid(row=3, column=0, columnspan=2, padx=5, pady=15, sticky=tk.W)
    
    def create_results_frame(self):
        """Create results display frame with all columns"""
        results_frame = ttk.LabelFrame(self.root, text="📊 Search Results", 
                                       style="Header.TLabelframe", padding=15)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Results count with icon
        count_frame = tk.Frame(results_frame, bg=self.bg_color)
        count_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.results_count_label = tk.Label(count_frame, text="🔍 No results yet", 
                                           font=("Segoe UI", 11, "bold"),
                                           fg=self.accent_color,
                                           bg=self.bg_color)
        self.results_count_label.pack(side=tk.LEFT)
        
        # Create a frame for treeview and scrollbars
        tree_frame = tk.Frame(results_frame, bg=self.bg_color)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define all columns matching CSV export
        columns = ("ID", "Text", "Metadata", "Region Main", "Region Main ID", 
                   "Region Sub", "Region Sub ID", "Date String", "Date Min", 
                   "Date Max", "Date Circa")
        
        # Create Treeview for results
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Define headings with icons
        self.tree.heading("ID", text="🆔 ID")
        self.tree.heading("Text", text="📜 Text")
        self.tree.heading("Metadata", text="📚 Metadata")
        self.tree.heading("Region Main", text="🌍 Main Region")
        self.tree.heading("Region Main ID", text="🔢 Main ID")
        self.tree.heading("Region Sub", text="📍 Sub Region")
        self.tree.heading("Region Sub ID", text="🔢 Sub ID")
        self.tree.heading("Date String", text="📅 Date String")
        self.tree.heading("Date Min", text="⬇️ Min Year")
        self.tree.heading("Date Max", text="⬆️ Max Year")
        self.tree.heading("Date Circa", text="🔄 Circa")
        
        # Define column widths
        self.tree.column("ID", width=80)
        self.tree.column("Text", width=300)
        self.tree.column("Metadata", width=250)
        self.tree.column("Region Main", width=150)
        self.tree.column("Region Main ID", width=100)
        self.tree.column("Region Sub", width=150)
        self.tree.column("Region Sub ID", width=100)
        self.tree.column("Date String", width=120)
        self.tree.column("Date Min", width=80)
        self.tree.column("Date Max", width=80)
        self.tree.column("Date Circa", width=80)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Use grid for tree_frame children only
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights for tree_frame
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_result_select)
        
        # Details text area
        details_frame = ttk.LabelFrame(results_frame, text="📖 Entry Details", 
                                      style="Header.TLabelframe", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Add text widget with custom font
        self.details_text = scrolledtext.ScrolledText(details_frame, height=10, 
                                                      wrap=tk.WORD,
                                                      font=("Consolas", 10),
                                                      bg="#fef9e7",
                                                      fg="#2c3e50")
        self.details_text.pack(fill=tk.BOTH, expand=True)
    
    def create_export_frame(self):
        """Create export frame with filename entry and export buttons"""
        export_frame = ttk.LabelFrame(self.root, text="💾 Export Results", 
                                      style="Header.TLabelframe", padding=15)
        export_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Left side - filename
        left_frame = tk.Frame(export_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(left_frame, text="📄 Output Filename:", 
                font=("Segoe UI", 10), bg=self.bg_color).pack(side=tk.LEFT, padx=5)
        
        self.output_filename_var = StringVar(value="search_results_packhum")
        self.filename_entry = ttk.Entry(left_frame, textvariable=self.output_filename_var, 
                                        width=35, font=("Segoe UI", 10))
        self.filename_entry.pack(side=tk.LEFT, padx=5)
        
        # Format indicators
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
        
        # Right side - buttons
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
            # Update colors for dark mode
            self.status_bar.config(bg="#34495e", fg="#ecf0f1")
        else:
            self.bg_color = "#f0f0f0"
            self.fg_color = "#333333"
            self.accent_color = "#2c3e50"
            self.status_bar.config(bg="#ecf0f1", fg="#7f8c8d")
        
        messagebox.showinfo("Theme", f"Theme changed to {'Dark' if self.dark_mode else 'Light'} mode.\nRestart the application for full effect.")
    
    def load_data(self, filename="iphi.json"):
        """Load JSON data in background thread"""
        self.status_bar.config(text=f"⏳ Loading {filename}...")
        self.search_button.config(state=tk.DISABLED)
        self.search_status.config(text="● Loading...", fg="#f39c12")
        
        def load():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
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
    
    def search(self):
        """Perform search based on filters"""
        if not self.data:
            messagebox.showwarning("Warning", "⚠️ Please load data first")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.details_text.delete(1.0, tk.END)
        
        # Build filters
        filters = {}
        
        # Basic filters
        if self.text_var.get().strip():
            filters['text'] = self.text_var.get().strip()
        if self.metadata_var.get().strip():
            filters['metadata'] = self.metadata_var.get().strip()
        if self.id_var.get().strip():
            try:
                filters['id'] = int(self.id_var.get().strip())
            except ValueError:
                messagebox.showwarning("Warning", "ID must be a number")
                return
        
        # Region filters (ID takes precedence)
        if self.region_main_id_var.get().strip():
            filters['region_main_id'] = self.region_main_id_var.get().strip()
        elif self.region_main_var.get().strip():
            filters['region_main'] = self.region_main_var.get().strip()
        
        if self.region_sub_id_var.get().strip():
            filters['region_sub_id'] = self.region_sub_id_var.get().strip()
        elif self.region_sub_var.get().strip():
            filters['region_sub'] = self.region_sub_var.get().strip()
        
        # Date filters
        if self.date_str_var.get().strip():
            filters['date_str'] = self.date_str_var.get().strip()
        if self.date_min_var.get().strip():
            filters['date_min'] = self.date_min_var.get().strip()
        if self.date_max_var.get().strip():
            filters['date_max'] = self.date_max_var.get().strip()
        if self.date_circa_var.get():
            filters['date_circa'] = True
        
        if not filters:
            messagebox.showwarning("Warning", "⚠️ Please enter at least one search filter")
            return
        
        # Perform search
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
        """Search entries based on filters"""
        results = []
        
        for entry in self.data:
            match = True
            for field, search_value in filters.items():
                field_value = entry.get(field, '')
                
                # Special handling for ID (exact match)
                if field == 'id':
                    if field_value != search_value:
                        match = False
                        break
                # Special handling for date_circa (boolean)
                elif field == 'date_circa':
                    if field_value != search_value:
                        match = False
                        break
                # For other fields, substring match (case-insensitive)
                else:
                    if search_value.lower() not in str(field_value).lower():
                        match = False
                        break
            
            if match:
                results.append(entry)
        
        return results
    
    def display_results(self, results):
        """Display search results in treeview with all columns"""
        self.current_results = results
        
        # Update count label
        result_icon = "🔍" if len(results) == 0 else "✅" if len(results) < 1000 else "📊"
        self.results_count_label.config(text=f"{result_icon} Found {len(results):,} matching entries")
        self.status_bar.config(text=f"✅ Search complete - {len(results):,} results found")
        self.search_button.config(state=tk.NORMAL)
        self.search_status.config(text="● Ready", fg=self.success_color)
        
        # Populate tree with all columns
        for result in results[:2000]:  # Limit to 2000 for performance
            self.tree.insert("", tk.END, values=(
                result.get('id', 'N/A'),
                result.get('text', 'N/A')[:200] + "..." if len(result.get('text', '')) > 200 else result.get('text', 'N/A'),
                result.get('metadata', 'N/A')[:150] + "..." if len(result.get('metadata', '')) > 150 else result.get('metadata', 'N/A'),
                result.get('region_main', 'N/A'),
                result.get('region_main_id', 'N/A'),
                result.get('region_sub', 'N/A'),
                result.get('region_sub_id', 'N/A'),
                result.get('date_str', 'N/A'),
                result.get('date_min', 'N/A'),
                result.get('date_max', 'N/A'),
                result.get('date_circa', 'N/A')
            ), tags=(result.get('id', ''),))
        
        if len(results) > 2000:
            self.status_bar.config(text=f"⚠️ Showing first 2000 of {len(results):,} results (use export for all)")
    
    def on_result_select(self, event):
        """Handle result selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get the ID from the selected item
        item = self.tree.item(selection[0])
        values = item['values']
        if not values:
            return
        
        # Find the full entry
        selected_id = values[0]
        full_entry = None
        
        for result in self.current_results:
            if result.get('id') == selected_id:
                full_entry = result
                break
        
        if full_entry:
            self.display_entry_details(full_entry)
    
    def display_entry_details(self, entry):
        """Display full entry details in text area"""
        self.details_text.delete(1.0, tk.END)
        
        # Format with better styling
        details = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              INSCRIPTION DETAILS                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ID: {str(entry.get('id', 'N/A')).ljust(67)}║
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
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                lines.append(current_line.ljust(width))
                current_line = word
        
        if current_line:
            lines.append(current_line.ljust(width))
        
        return "\n║ ".join(lines)
    
    def export_results_csv(self):
        """Export current results to CSV with user-specified filename"""
        if not self.current_results:
            messagebox.showwarning("Warning", "⚠️ No results to export")
            return
        
        # Get filename from entry
        base_filename = self.output_filename_var.get().strip()
        if not base_filename:
            base_filename = "search_results_packhum"
        
        filename = f"{base_filename}.csv"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            title="Save CSV file",
            initialfile=filename,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Complete field list matching the CSV from command line version
                fieldnames = ['id', 'text', 'metadata', 'region_main', 'region_main_id',
                             'region_sub', 'region_sub_id', 'date_str', 'date_min', 
                             'date_max', 'date_circa']
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(self.current_results)
                
                messagebox.showinfo("Success", f"✅ Exported {len(self.current_results):,} results to {filename}")
                self.status_bar.config(text=f"✅ Exported {len(self.current_results):,} results to CSV")
            except Exception as e:
                messagebox.showerror("Error", f"❌ Failed to export: {str(e)}")
    
    def export_results_xml(self):
        """Export current results to XML with user-specified filename"""
        if not self.current_results:
            messagebox.showwarning("Warning", "⚠️ No results to export")
            return
        
        # Get filename from entry
        base_filename = self.output_filename_var.get().strip()
        if not base_filename:
            base_filename = "search_results_packhum"
        
        filename = f"{base_filename}.xml"
        
        # Ask for save location
        filename = filedialog.asksaveasfilename(
            title="Save XML file",
            initialfile=filename,
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Create root element
                root = ET.Element("search_results")
                root.set("total_results", str(len(self.current_results)))
                root.set("export_date", datetime.now().isoformat())
                
                # Add each entry
                for entry in self.current_results:
                    entry_elem = ET.SubElement(root, "entry")
                    
                    # Add all fields
                    for key, value in entry.items():
                        if value is not None:
                            field_elem = ET.SubElement(entry_elem, key)
                            field_elem.text = str(value)
                        else:
                            field_elem = ET.SubElement(entry_elem, key)
                            field_elem.text = ""
                            field_elem.set("nil", "true")
                
                # Pretty print XML
                xml_str = ET.tostring(root, encoding='unicode')
                dom = minidom.parseString(xml_str)
                pretty_xml = dom.toprettyxml(indent="  ")
                
                # Write to file
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(pretty_xml)
                
                messagebox.showinfo("Success", f"✅ Exported {len(self.current_results):,} results to {filename}")
                self.status_bar.config(text=f"✅ Exported {len(self.current_results):,} results to XML")
            except Exception as e:
                messagebox.showerror("Error", f"❌ Failed to export XML: {str(e)}")
    
    def clear_filters(self):
        """Clear all filter fields"""
        self.text_var.set("")
        self.metadata_var.set("")
        self.id_var.set("")
        self.region_main_id_var.set("")
        self.region_main_var.set("")
        self.region_sub_id_var.set("")
        self.region_sub_var.set("")
        self.date_str_var.set("")
        self.date_min_var.set("")
        self.date_max_var.set("")
        self.date_circa_var.set(False)
        
        # Clear results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.details_text.delete(1.0, tk.END)
        self.results_count_label.config(text="🔍 No results yet")
        self.current_results = []
        self.status_bar.config(text="🗑 Filters cleared")
        self.search_status.config(text="● Ready", fg=self.success_color)
    

    def show_about(self):
        """Show about dialog"""
        about_text = """🏛️ Veatriki, a Packhum search and export tool by Beatrice "Bice" Pavesi
═══════════════════════════════════

A graphical interface for searching the Packard Humanities Institute (PHI) database of Greek inscriptions.

✨ Features:
• Search by text, metadata, and ID
• Search by region (name or ID)
• Search by date criteria
• Export results to CSV or XML
• Real-time search results
• Detailed inscription viewer

📊 Database stats:
Contains over 178,000 inscriptions, covering most of PHI's  Greek epigraphy collection, except entries with more than 10 percent latin text.


🔧 Technical:
• Built with Python and tkinter
• Supports case-insensitive search
• Threaded operations for smooth UI

📚 Requires:
• Python 3.7+
• iphi.json by Sommerschield et al. (https://github.com/sommerschield/iphi.git)

Version 1.0
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
• Use partial words - search is case-insensitive
• Region ID takes precedence over region name
• BCE years are negative numbers (e.g., -275)
• Export all results (no limit in CSV/XML)
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)

def main():
    root = tk.Tk()
    app = PackhumSearchGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
