from explorer.explorer import LibertyExplorer
from .utils import to_float
from .pin import Pin


class Cell:
    def __init__(self, cell: LibertyExplorer):
        self.cell = cell

        self.name = cell.name
        self.area = to_float(cell.get("area"))

        self.input_pins = {}
        self.output_pins = {}
        self.timing_arcs = []

        # resultados de compute — vacíos hasta que se llame compute()
        self.cell_rise = None
        self.cell_fall = None
        self.rise_transition = None
        self.fall_transition = None

        self.tp = None
        self.slew_out = None

        self.worst_arc = None
        self.computed = False

        self.setPinInfo()

    def setPinInfo(self):
        for pin_group in self.cell.children("pin"):
            pin = Pin(pin_group)

            if pin.direction == "input":
                self.input_pins[pin.name] = pin

            elif pin.direction == "output":
                self.output_pins[pin.name] = pin
                self.timing_arcs.extend(pin.timing_arcs)

    def getInputCapacitance(self):
        capacitance = 0
        for pin in self.input_pins.values():
            if pin.capacitance is not None:
                capacitance += pin.capacitance
        return capacitance

    def compute(self, input_slew, output_load):
        if len(self.timing_arcs) == 0:
            return None

        worst_delay = 0

        # evaluar todos los arcs, quedarse con el peor
        for arc in self.timing_arcs:
            r = arc.compute(input_slew, output_load)

            delay_rise = r["cell_rise"]["value"]
            delay_fall = r["cell_fall"]["value"]
            delay = max(delay_rise, delay_fall)

            if delay > worst_delay:
                worst_delay = delay
                self.worst_arc = arc
                self.cell_rise = r["cell_rise"]["value"]
                self.cell_fall = r["cell_fall"]["value"]
                self.rise_transition = r["rise_transition"]["value"]
                self.fall_transition = r["fall_transition"]["value"]

        self.tp = max(self.cell_rise, self.cell_fall)
        self.slew_out = max(self.rise_transition, self.fall_transition)
        self.computed = True

        return {
            "cell": self.name,
            "arc": f"{self.worst_arc.related_pin} -> {self.worst_arc.output_pin}",
            "cell_rise": self.cell_rise,
            "cell_fall": self.cell_fall,
            "rise_transition": self.rise_transition,
            "fall_transition": self.fall_transition,
            "tp": self.tp,
            "slew_out": self.slew_out,
        }

    def print_info(self, show_values=False):
        print("=" * 80)
        print(f"Cell: {self.name}")
        print(f"Area: {self.area}")
        print("=" * 80)

        print("\nINPUT PINS")
        print("-" * 80)

        if len(self.input_pins) == 0:
            print("No input pins found.")
        else:
            for pin_name, pin in self.input_pins.items():
                print(f"Pin: {pin_name}")
                print(f"  direction   : {pin.direction}")
                print(f"  capacitance : {pin.capacitance}")

        print("\nOUTPUT PINS")
        print("-" * 80)

        if len(self.output_pins) == 0:
            print("No output pins found.")
        else:
            for pin_name, pin in self.output_pins.items():
                print(f"Pin: {pin_name}")
                print(f"  direction    : {pin.direction}")
                print(f"  capacitance  : {pin.capacitance}")
                print(f"  timing arcs  : {len(pin.timing_arcs)}")

        print("\nTIMING ARCS")
        print("-" * 80)

        if len(self.timing_arcs) == 0:
            print("No timing arcs found.")
        else:
            for i, arc in enumerate(self.timing_arcs, start=1):
                print(f"\nArc #{i}")
                print(f"  output_pin   : {arc.output_pin}")
                print(f"  related_pin  : {arc.related_pin}")
                print(f"  timing_sense : {arc.timing_sense}")
                print(f"  timing_type  : {arc.timing_type}")

                print("  LUTs:")

                if len(arc.luts) == 0:
                    print("    No LUTs found.")
                else:
                    for lut_name, lut in arc.luts.items():
                        rows = len(lut.values)
                        cols = len(lut.values[0]) if rows > 0 else 0

                        print(f"    {lut_name}")
                        print(f"      template : {lut.template}")
                        print(f"      index_1  : {lut.index_1}")
                        print(f"      index_2  : {lut.index_2}")
                        print(f"      shape    : {rows} x {cols}")

                        if show_values:
                            print(f"      values   :")
                            for row in lut.values:
                                print(f"        {row}")

        if self.computed:
            print(f"\nCOMPUTED RESULTS (worst arc: {self.worst_arc.related_pin} -> {self.worst_arc.output_pin})")
            print("-" * 80)
            print(f"  cell_rise        : {self.cell_rise:.6f} ns")
            print(f"  cell_fall        : {self.cell_fall:.6f} ns")
            print(f"  rise_transition  : {self.rise_transition:.6f} ns")
            print(f"  fall_transition  : {self.fall_transition:.6f} ns")
            print(f"  tp               : {self.tp:.6f} ns")
            print(f"  slew_out         : {self.slew_out:.6f} ns")

        print("\n" + "=" * 80)

    def summary(self):
        print(f"Cell: {self.name}")
        print(f"Area: {self.area}")
        print(f"Input pins: {list(self.input_pins.keys())}")
        print(f"Output pins: {list(self.output_pins.keys())}")
        print(f"Timing arcs: {len(self.timing_arcs)}")
        if self.computed:
            print(f"tp: {self.tp:.6f} ns  slew_out: {self.slew_out:.6f} ns")