import tkinter as tk
from tkinter import ttk, filedialog, messagebox


from .cells_tab import CellsTabMixin
from .detail_tab import DetailTabMixin
from .path_tab import PathBuilderMixin


class LibertyGUI(CellsTabMixin, DetailTabMixin, PathBuilderMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("LibertyScope")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        self.lib = None
        self.chain = []
        self._selected_cell = None

        self._build_menu()
        self._build_ui()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open .lib", command=self._open_lib)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_cells = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cells, text="Cells")
        self._build_cells_tab()

        self.tab_detail = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_detail, text="Cell Detail")
        self._build_detail_tab()

        self.tab_path = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_path, text="Path Builder")
        self._build_path_tab()

        self.status_var = tk.StringVar(value="No library loaded. File > Open .lib")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill="x", side="bottom")

    def _open_lib(self):
        path = filedialog.askopenfilename(
            title="Open Liberty File",
            filetypes=[("Liberty files", "*.lib"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            from library.library import Library

            self.lib = Library(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load library:\n{e}")
            return

        self.status_var.set(
            f"{self.lib.name}  |  {len(self.lib.cells.cells)} cells  |  "
            f"{self.lib.time_unit}  |  {self.lib.nom_voltage}V  {self.lib.nom_temperature}°C"
        )

        self._populate_cells()
        self._populate_path_combos()
        self._clear_chain()
