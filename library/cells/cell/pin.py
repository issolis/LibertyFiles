from libertyscope.explorer import LibertyExplorer
from .utils import clean_str, to_float
from .timingArc import TimingArc

class Pin:
    def __init__(self, pin: LibertyExplorer):
        self.name = pin.name
        self.direction = clean_str(pin.get("direction"))
        self.capacitance = to_float(pin.get("capacitance"))
        
        
        self.input_slew = 0; 
        self.output_slew = 0; 

        self.timing_arcs: list[TimingArc] = []

        if self.direction == "output":
            for timing in pin.children("timing"):
                arc = TimingArc(timing, self.name)
                if arc.is_propagation():
                    self.timing_arcs.append(arc)
                    
        
                    
    