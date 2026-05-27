from explorer.explorer import LibertyExplorer
from  .utils import to_float_list, to_float_matrix


from bisect import bisect_right


class Lut:
    def __init__(self, lut):
        self.name = lut.kind
        self.template = lut.name

        self.index_1 = to_float_list(lut.get("index_1"))
        self.index_2 = to_float_list(lut.get("index_2"))
        self.values = to_float_matrix(lut.get("values"))

    def _clamp(self, x, axis):
        was_clamped = False

        
    
        if x < axis[0]:
            x = axis[0]
            was_clamped = True

        elif x > axis[-1]:
            x = axis[-1]
            was_clamped = True

        return x, was_clamped

    def _find_bounds(self, x, axis):
        if x <= axis[0]:
            return 0, 1

        if x >= axis[-1]:
            return len(axis) - 2, len(axis) - 1

        i1 = bisect_right(axis, x)
        i0 = i1 - 1

        return i0, i1

    def lookup(self, input_slew, output_load):
        x, clamped_x = self._clamp(input_slew, self.index_1)
        y, clamped_y = self._clamp(output_load, self.index_2)

        i0, i1 = self._find_bounds(x, self.index_1)
        j0, j1 = self._find_bounds(y, self.index_2)

        x0 = self.index_1[i0]
        x1 = self.index_1[i1]

        y0 = self.index_2[j0]
        y1 = self.index_2[j1]

        q00 = self.values[i0][j0]
        q10 = self.values[i1][j0]
        q01 = self.values[i0][j1]
        q11 = self.values[i1][j1]

        u = (x - x0) / (x1 - x0)
        v = (y - y0) / (y1 - y0)

        value = (
            (1 - u) * (1 - v) * q00
            + u * (1 - v) * q10
            + (1 - u) * v * q01
            + u * v * q11
        )

        return {
            "value": value,
            "input_slew_used": x,
            "output_load_used": y,
            "input_slew_clamped": clamped_x,
            "output_load_clamped": clamped_y,
            "extrapolated": clamped_x or clamped_y,
            "bounds": {
                "i0": i0,
                "i1": i1,
                "j0": j0,
                "j1": j1, 
            },
        }

    def lookup_1d(self, output_load, input_slew=None):
        if input_slew is not None:
            diffs = [abs(s - input_slew) for s in self.index_1]
            row = diffs.index(min(diffs))
        else:
            row = 0
        return self.lookup_1d_fixed_row(output_load, row=row)

    def lookup_1d_fixed_row(self, output_load, row=0):
        y, clamped_y = self._clamp(output_load, self.index_2)
        j0, j1 = self._find_bounds(y, self.index_2)

        y0 = self.index_2[j0]
        y1 = self.index_2[j1]

        q0 = self.values[row][j0]
        q1 = self.values[row][j1]

        v = (y - y0) / (y1 - y0)
        value = (1 - v) * q0 + v * q1

        return {
            "value": value,
            "row_used": row,
            "output_load_clamped": clamped_y,
        }