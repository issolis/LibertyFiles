from explorer.explorer import load_liberty, LibertyExplorer
from explorer.explorer import load_liberty, LibertyExplorer
from .cells.cells import Cells


class Library:
    def __init__(self, path):
        self.library: LibertyExplorer = load_liberty(path)
        self.name: str = self.library.name
        self.delay_model: str = self.library.get("delay_model")
        self.time_unit: str = str(self.library.get("time_unit")).strip('"')

        cap_load = self.library.get("capacitive_load_unit")
        self.cap_load_unit: tuple = (cap_load[0], str(cap_load[1]))

        self.nom_voltage: float = self.library.get("nom_voltage")
        self.nom_temperature: float = self.library.get("nom_temperature")
        
        self.cells: Cells = Cells(self.library.children("cell"))
        
    def findCell(self, name):
        for cell in self.cells.cells:
            if cell.name == name:
                return cell
        return None
