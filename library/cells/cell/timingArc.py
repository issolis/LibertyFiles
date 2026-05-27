from explorer.explorer import LibertyExplorer
from .lut import Lut
from .utils import clean_str

class TimingArc:
    PROPAGATION_TYPES = {None, "None", "rising_edge", "falling_edge"}

    def __init__(self, timing: LibertyExplorer, output_pin_name: str):
        self.output_pin = output_pin_name

        self.related_pin = clean_str(timing.get("related_pin"))
        self.timing_sense = clean_str(timing.get("timing_sense"))
        self.timing_type = clean_str(timing.get("timing_type"))

        self.luts = {}

        for lut_name in [
            "cell_rise",
            "cell_fall",
            "rise_transition",
            "fall_transition",
        ]:
            lut_groups = timing.children(lut_name)

            if len(lut_groups) > 0:
                self.luts[lut_name] = Lut(lut_groups[0])

    def is_propagation(self):
        return self.timing_type in self.PROPAGATION_TYPES and len(self.luts) == 4

    def compute(self, input_slew, output_load):
        result = {}
        for lut_name, lut in self.luts.items():
            result[lut_name] = lut.lookup(input_slew, output_load)
        return result

    def compute_1d(self, output_load):
        result = {}
        for lut_name, lut in self.luts.items():
            result[lut_name] = lut.lookup_1d(output_load)
        return result