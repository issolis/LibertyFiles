import tkinter as tk
from tkinter import ttk, messagebox


class PathBuilderMixin:
    def _build_path_tab(self):
        ctrl_frame = ttk.LabelFrame(self.tab_path, text="Add Stage")
        ctrl_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(ctrl_frame, text="Cell:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.path_cell_var = tk.StringVar()
        self.path_cell_combo = ttk.Combobox(ctrl_frame, textvariable=self.path_cell_var, width=15, state="readonly")
        self.path_cell_combo.grid(row=0, column=1, padx=5, sticky="w")
        self.path_cell_combo.bind("<<ComboboxSelected>>", self._on_path_cell_select)

        ttk.Label(ctrl_frame, text="Input Pins:").grid(row=0, column=2, padx=5, sticky="nw")
        input_frame = ttk.Frame(ctrl_frame)
        input_frame.grid(row=0, column=3, padx=5, sticky="w")
        self.path_input_list = tk.Listbox(
            input_frame,
            height=4,
            width=12,
            selectmode="extended",
            exportselection=False,
        )
        input_scroll = ttk.Scrollbar(input_frame, orient="vertical", command=self.path_input_list.yview)
        self.path_input_list.configure(yscrollcommand=input_scroll.set)
        self.path_input_list.pack(side="left", fill="y")
        input_scroll.pack(side="left", fill="y")

        ttk.Label(ctrl_frame, text="Output Pin:").grid(row=0, column=4, padx=5, sticky="w")
        self.path_output_var = tk.StringVar()
        self.path_output_combo = ttk.Combobox(ctrl_frame, textvariable=self.path_output_var, width=8, state="readonly")
        self.path_output_combo.grid(row=0, column=5, padx=5, sticky="w")

        ttk.Button(ctrl_frame, text="Add", command=self._add_stage).grid(row=0, column=6, padx=10, sticky="w")
        ttk.Button(ctrl_frame, text="Remove Last", command=self._remove_stage).grid(row=0, column=7, padx=5, sticky="w")
        ttk.Button(ctrl_frame, text="Clear All", command=self._clear_chain).grid(row=0, column=8, padx=5, sticky="w")

        hint = "Use Ctrl/Shift to select more than one input pin."
        ttk.Label(ctrl_frame, text=hint).grid(row=1, column=3, columnspan=4, sticky="w", padx=5, pady=(2, 0))

        chain_frame = ttk.LabelFrame(self.tab_path, text="Chain")
        chain_frame.pack(fill="both", expand=True, padx=5, pady=5)

        chain_cols = ("stage", "cell", "arc", "input_slew", "output_load", "tp", "slew_out")
        self.chain_tree = ttk.Treeview(chain_frame, columns=chain_cols, show="headings", height=8)
        self.chain_tree.heading("stage", text="#")
        self.chain_tree.heading("cell", text="Cell")
        self.chain_tree.heading("arc", text="Arc")
        self.chain_tree.heading("input_slew", text="Input Slew (ns)")
        self.chain_tree.heading("output_load", text="C_L (fF)")
        self.chain_tree.heading("tp", text="tp (ns)")
        self.chain_tree.heading("slew_out", text="Slew Out (ns)")

        self.chain_tree.column("stage", width=40, anchor="center")
        self.chain_tree.column("cell", width=120)
        self.chain_tree.column("arc", width=180)
        self.chain_tree.column("input_slew", width=120, anchor="e")
        self.chain_tree.column("output_load", width=100, anchor="e")
        self.chain_tree.column("tp", width=100, anchor="e")
        self.chain_tree.column("slew_out", width=120, anchor="e")
        self.chain_tree.pack(fill="both", expand=True)

        calc_frame = ttk.Frame(self.tab_path)
        calc_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(calc_frame, text="Initial Slew (ns):").pack(side="left", padx=5)
        self.chain_slew = ttk.Entry(calc_frame, width=12)
        self.chain_slew.insert(0, "0.04")
        self.chain_slew.pack(side="left", padx=5)

        ttk.Label(calc_frame, text="Final Load (fF):").pack(side="left", padx=5)
        self.chain_load = ttk.Entry(calc_frame, width=12)
        self.chain_load.insert(0, "0.0")
        self.chain_load.pack(side="left", padx=5)

        ttk.Button(calc_frame, text="Compute Chain", command=self._compute_chain).pack(side="left", padx=10)

        self.chain_result = tk.StringVar()
        ttk.Label(calc_frame, textvariable=self.chain_result, font=("Courier", 11, "bold")).pack(side="left", padx=15)

    def _populate_path_combos(self):
        cell_names = [c.name for c in self.lib.cells.cells if len(c.timing_arcs) > 0]
        self.path_cell_combo["values"] = cell_names

    def _on_path_cell_select(self, event):
        cell_name = self.path_cell_var.get()
        cell = self.lib.findCell(cell_name)
        if cell is None:
            return

        input_pins = set()
        output_pins = set()
        for arc in cell.timing_arcs:
            input_pins.add(arc.related_pin)
            output_pins.add(arc.output_pin)

        sorted_inputs = sorted(input_pins)
        self.path_input_list.delete(0, tk.END)
        for pin_name in sorted_inputs:
            self.path_input_list.insert(tk.END, pin_name)

        if len(sorted_inputs) == 1:
            self.path_input_list.selection_set(0)

        sorted_outputs = sorted(output_pins)
        self.path_output_combo["values"] = sorted_outputs
        self.path_output_var.set(sorted_outputs[0] if len(sorted_outputs) == 1 else "")

    def _get_selected_path_inputs(self):
        return [self.path_input_list.get(i) for i in self.path_input_list.curselection()]

    def _stage_input_pins(self, entry):
        if "input_pins" in entry:
            return list(entry["input_pins"])
        if "input_pin" in entry:
            return [entry["input_pin"]]
        return []

    def _add_stage(self):
        cell_name = self.path_cell_var.get()
        input_pins = self._get_selected_path_inputs()
        output_pin = self.path_output_var.get()

        if not cell_name or not input_pins or not output_pin:
            messagebox.showwarning("Warning", "Select cell, at least one input pin, and output pin.")
            return

        self.chain.append({
            "cell": cell_name,
            "input_pins": input_pins,
            "output_pin": output_pin,
        })

        self._refresh_chain_tree()

    def _remove_stage(self):
        if self.chain:
            self.chain.pop()
            self._refresh_chain_tree()

    def _clear_chain(self):
        self.chain = []
        self._refresh_chain_tree()
        self.chain_result.set("")

    def _refresh_chain_tree(self):
        self.chain_tree.delete(*self.chain_tree.get_children())
        for i, stage in enumerate(self.chain, 1):
            input_pins = self._stage_input_pins(stage)
            self.chain_tree.insert("", "end", values=(
                i,
                stage["cell"],
                f"{', '.join(input_pins)} -> {stage['output_pin']}",
                "-", "-", "-", "-",
            ))
        self.chain_result.set("")

    def _compute_chain(self):
        if not self.chain:
            messagebox.showwarning("Warning", "Add at least one stage.")
            return

        try:
            initial_slew = float(self.chain_slew.get())
            final_load = float(self.chain_load.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid slew or load value.")
            return

        stages = []
        for entry in self.chain:
            cell = self.lib.findCell(entry["cell"])
            if cell is None:
                messagebox.showerror("Error", f"Cell '{entry['cell']}' not found.")
                return

            selected_input_pins = self._stage_input_pins(entry)
            arcs = []
            missing_arcs = []
            for input_pin in selected_input_pins:
                arc = self._find_timing_arc(cell, input_pin, entry["output_pin"])
                if arc is None:
                    missing_arcs.append(input_pin)
                else:
                    arcs.append(arc)

            if missing_arcs:
                pins = ", ".join(missing_arcs)
                messagebox.showerror(
                    "Error",
                    f"No arc from input pin(s) '{pins}' to output '{entry['output_pin']}' in '{cell.name}'.",
                )
                return

            stages.append({"cell": cell, "arcs": arcs, "entry": entry})

        loads = []
        for i in range(len(stages)):
            if i + 1 < len(stages):
                next_cell = stages[i + 1]["cell"]
                next_inputs = self._stage_input_pins(stages[i + 1]["entry"])
                loads.append(self._sum_input_capacitance(next_cell, next_inputs))
            else:
                loads.append(final_load)

        self.chain_tree.delete(*self.chain_tree.get_children())
        current_slew = initial_slew
        total_delay = 0.0

        for i, (stage, load) in enumerate(zip(stages, loads), 1):
            cell = stage["cell"]
            best = self._compute_worst_stage_arc(stage["arcs"], current_slew, load)

            total_delay += best["tp"]

            selected_inputs = self._stage_input_pins(stage["entry"])
            arc_text = (
                f"{', '.join(selected_inputs)} -> {best['arc'].output_pin}"
                f"  | worst: {best['arc'].related_pin}"
            )

            self.chain_tree.insert("", "end", values=(
                i,
                cell.name,
                arc_text,
                f"{current_slew:.6f}",
                f"{load:.4f}",
                f"{best['tp']:.6f}",
                f"{best['slew_out']:.6f}",
            ))

            current_slew = best["slew_out"]

        self.chain_result.set(f"Total tp = {total_delay:.6f} ns  |  Final slew = {current_slew:.6f} ns")

    def _find_timing_arc(self, cell, input_pin, output_pin):
        for arc in cell.timing_arcs:
            if arc.related_pin == input_pin and arc.output_pin == output_pin:
                return arc
        return None

    def _sum_input_capacitance(self, cell, input_pins):
        capacitance = 0.0
        for input_pin in input_pins:
            pin = cell.input_pins.get(input_pin)
            if pin is not None and pin.capacitance is not None:
                capacitance += pin.capacitance
        return capacitance

    def _compute_worst_stage_arc(self, arcs, input_slew, output_load):
        worst = None
        for arc in arcs:
            result = arc.compute(input_slew, output_load)
            delay_rise = result["cell_rise"]["value"]
            delay_fall = result["cell_fall"]["value"]
            slew_rise = result["rise_transition"]["value"]
            slew_fall = result["fall_transition"]["value"]

            candidate = {
                "arc": arc,
                "tp": max(delay_rise, delay_fall),
                "slew_out": max(slew_rise, slew_fall),
            }

            if worst is None or candidate["tp"] > worst["tp"]:
                worst = candidate

        return worst
