import tkinter as tk
from tkinter import ttk, messagebox


class DetailTabMixin:
    def _build_detail_tab(self):
        info_frame = ttk.LabelFrame(self.tab_detail, text="Cell Info")
        info_frame.pack(fill="x", padx=5, pady=5)

        self.detail_name = tk.StringVar()
        self.detail_area = tk.StringVar()
        self.detail_cap = tk.StringVar()

        ttk.Label(info_frame, text="Cell:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(info_frame, textvariable=self.detail_name, font=("", 11, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(info_frame, text="Area:").grid(row=0, column=2, sticky="w", padx=15)
        ttk.Label(info_frame, textvariable=self.detail_area).grid(row=0, column=3, sticky="w")
        ttk.Label(info_frame, text="Input Cap:").grid(row=0, column=4, sticky="w", padx=15)
        ttk.Label(info_frame, textvariable=self.detail_cap).grid(row=0, column=5, sticky="w")

        paned = ttk.PanedWindow(self.tab_detail, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        pin_frame = ttk.LabelFrame(paned, text="Pins")
        paned.add(pin_frame, weight=1)

        pin_cols = ("name", "direction", "capacitance")
        self.pin_tree = ttk.Treeview(pin_frame, columns=pin_cols, show="headings", height=10)
        self.pin_tree.heading("name", text="Pin")
        self.pin_tree.heading("direction", text="Direction")
        self.pin_tree.heading("capacitance", text="Cap (fF)")
        self.pin_tree.column("name", width=80)
        self.pin_tree.column("direction", width=80)
        self.pin_tree.column("capacitance", width=80, anchor="e")
        self.pin_tree.pack(fill="both", expand=True)

        arc_frame = ttk.LabelFrame(paned, text="Timing Arcs")
        paned.add(arc_frame, weight=2)

        arc_cols = ("related", "output", "sense", "type", "luts")
        self.arc_tree = ttk.Treeview(arc_frame, columns=arc_cols, show="headings", height=10)
        self.arc_tree.heading("related", text="Input Pin")
        self.arc_tree.heading("output", text="Output Pin")
        self.arc_tree.heading("sense", text="Sense")
        self.arc_tree.heading("type", text="Type")
        self.arc_tree.heading("luts", text="LUTs")
        self.arc_tree.column("related", width=80)
        self.arc_tree.column("output", width=80)
        self.arc_tree.column("sense", width=120)
        self.arc_tree.column("type", width=100)
        self.arc_tree.column("luts", width=200)
        self.arc_tree.pack(fill="both", expand=True)

        compute_frame = ttk.LabelFrame(self.tab_detail, text="Compute")
        compute_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(compute_frame, text="Input Slew (ns):").grid(row=0, column=0, padx=5, pady=3)
        self.detail_slew = ttk.Entry(compute_frame, width=12)
        self.detail_slew.insert(0, "0.05")
        self.detail_slew.grid(row=0, column=1, padx=5)

        ttk.Label(compute_frame, text="Output Load (fF):").grid(row=0, column=2, padx=5)
        self.detail_load = ttk.Entry(compute_frame, width=12)
        self.detail_load.insert(0, "10.0")
        self.detail_load.grid(row=0, column=3, padx=5)

        ttk.Button(compute_frame, text="Compute", command=self._compute_cell).grid(row=0, column=4, padx=10)

        self.compute_result = tk.StringVar()
        ttk.Label(compute_frame, textvariable=self.compute_result, font=("Courier", 10)).grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            padx=5,
            pady=3,
        )

    def _on_cell_select(self, event):
        selection = self.cell_tree.selection()
        if not selection:
            return

        cell_name = selection[0]
        cell = self.lib.findCell(cell_name)
        if cell is None:
            return

        self.detail_name.set(cell.name)
        self.detail_area.set(f"{cell.area}" if cell.area else "-")
        self.detail_cap.set(f"{cell.getInputCapacitance():.4f} fF" if cell.input_pins else "-")

        self.pin_tree.delete(*self.pin_tree.get_children())
        for pin_name, pin in cell.input_pins.items():
            cap = f"{pin.capacitance:.4f}" if pin.capacitance else "-"
            self.pin_tree.insert("", "end", values=(pin_name, "input", cap))
        for pin_name, pin in cell.output_pins.items():
            cap = f"{pin.capacitance:.4f}" if pin.capacitance else "-"
            self.pin_tree.insert("", "end", values=(pin_name, "output", cap))

        self.arc_tree.delete(*self.arc_tree.get_children())
        for arc in cell.timing_arcs:
            lut_names = ", ".join(arc.luts.keys())
            self.arc_tree.insert("", "end", values=(
                arc.related_pin,
                arc.output_pin,
                arc.timing_sense or "-",
                arc.timing_type or "combinational",
                lut_names,
            ))

        self.compute_result.set("")
        self.notebook.select(self.tab_detail)
        self._selected_cell = cell

    def _compute_cell(self):
        if self._selected_cell is None:
            messagebox.showwarning("Warning", "Select a cell first.")
            return

        try:
            slew = float(self.detail_slew.get())
            load = float(self.detail_load.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid slew or load value.")
            return

        cell = self._selected_cell
        result = cell.compute(slew, load)

        if result is None:
            self.compute_result.set("No timing arcs to compute.")
            return

        self.compute_result.set(
            f"tp={cell.tp:.6f} ns  |  slew_out={cell.slew_out:.6f} ns  |  "
            f"rise={cell.cell_rise:.6f}  fall={cell.cell_fall:.6f}  |  "
            f"arc: {cell.worst_arc.related_pin}->{cell.worst_arc.output_pin}"
        )
