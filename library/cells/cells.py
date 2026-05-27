from libertyscope.explorer import LibertyExplorer

from .cell.cell import Cell


class Cells:
    def __init__(self, cells:list[LibertyExplorer]): 
        self.cells = [ Cell(cell) for cell in cells]