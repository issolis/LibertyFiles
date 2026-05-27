from library.library import Library


lib = Library("NangateOpenCellLibrary_typical.lib")

targets = ["INV_X1", "AND2_X1", "NAND2_X1", "DFF_X1"]

input_slew = 0.05
output_load = 10.0


def findCell(name):
    for cell in lib.cells.cells:
        if cell.name == name:
            return cell
    return None


print("=" * 80)
print(f"COMPUTE por celda  (input_slew={input_slew}, output_load={output_load})")
print("=" * 80)

for cell in lib.cells.cells:
    if cell.name not in targets:
        continue

    cell.compute(input_slew, output_load)

    print(f"\n{cell.name}  (worst arc: {cell.worst_arc.related_pin} -> {cell.worst_arc.output_pin})")
    print(f"  cell_rise        = {cell.cell_rise:.6f} ns")
    print(f"  cell_fall        = {cell.cell_fall:.6f} ns")
    print(f"  rise_transition  = {cell.rise_transition:.6f} ns")
    print(f"  fall_transition  = {cell.fall_transition:.6f} ns")
    print(f"  tp               = {cell.tp:.6f} ns")
    print(f"  slew_out         = {cell.slew_out:.6f} ns")


# cadena del paper: propagar slew
print("\n" + "=" * 80)
print("CADENA: INV_X1 -> AND2_X1 -> DFF_X1")
print("=" * 80)

inv = findCell("INV_X1")
and2 = findCell("AND2_X1")
dff = findCell("DFF_X1")

# etapa 1
inv.compute(input_slew=0.04, output_load=and2.input_pins["A1"].capacitance)
print(f"\nINV_X1:  tp={inv.tp:.6f} ns  slew_out={inv.slew_out:.6f} ns")

# etapa 2: input_slew = slew_out del INV
and2.compute(input_slew=inv.slew_out, output_load=dff.input_pins["CK"].capacitance)
print(f"AND2_X1: tp={and2.tp:.6f} ns  slew_out={and2.slew_out:.6f} ns")

# etapa 3: input_slew = slew_out del AND
dff.compute(input_slew=and2.slew_out, output_load=0.0)
print(f"DFF_X1:  tp={dff.tp:.6f} ns  slew_out={dff.slew_out:.6f} ns")

total = inv.tp + and2.tp + dff.tp
print(f"\nTOTAL PATH DELAY = {total:.6f} ns")