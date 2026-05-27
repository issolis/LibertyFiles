from tkinter import ttk


class CellsTabMixin:
    def _build_cells_tab(self):
        cols = ("name", "area", "inputs", "outputs", "arcs", "input_cap")
        self.cell_tree = ttk.Treeview(
            self.tab_cells,
            columns=cols,
            show="headings",
            selectmode="browse",
        )

        self.cell_tree.heading("name", text="Cell")
        self.cell_tree.heading("area", text="Area")
        self.cell_tree.heading("inputs", text="Input Pins")
        self.cell_tree.heading("outputs", text="Output Pins")
        self.cell_tree.heading("arcs", text="Timing Arcs")
        self.cell_tree.heading("input_cap", text="Input Cap (fF)")

        self.cell_tree.column("name", width=150)
        self.cell_tree.column("area", width=80, anchor="e")
        self.cell_tree.column("inputs", width=120)
        self.cell_tree.column("outputs", width=120)
        self.cell_tree.column("arcs", width=80, anchor="e")
        self.cell_tree.column("input_cap", width=100, anchor="e")

        scrollbar = ttk.Scrollbar(self.tab_cells, orient="vertical", command=self.cell_tree.yview)
        self.cell_tree.configure(yscrollcommand=scrollbar.set)

        self.cell_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.cell_tree.bind("<<TreeviewSelect>>", self._on_cell_select)

    def _populate_cells(self):
        self.cell_tree.delete(*self.cell_tree.get_children())

        for cell in self.lib.cells.cells:
            inputs = ", ".join(cell.input_pins.keys()) if cell.input_pins else "-"
            outputs = ", ".join(cell.output_pins.keys()) if cell.output_pins else "-"
            cap = f"{cell.getInputCapacitance():.4f}" if cell.input_pins else "-"

            self.cell_tree.insert("", "end", iid=cell.name, values=(
                cell.name,
                f"{cell.area}" if cell.area else "-",
                inputs,
                outputs,
                len(cell.timing_arcs),
                cap,
            ))
