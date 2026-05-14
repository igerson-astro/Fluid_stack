from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit

pressure = .10136e6
area = .0003835
eps = .015e-3

JP8 = Fluid(
    name = "JP8.mix",
    temperature = 323.15,
    pressure = pressure
)


circuit = Circuit(
    fluid = JP8,
    mdot = 2,
    static_pressure = pressure
)

LP_pump = circuit.pump(
    dP = 0.2206e6,
    name = "LP_pump"
)


tube1 = circuit.tube_length(
    length = 1,
    ID = .022098,
    eps = eps,
    name = "tube_1"
)

bend1 = circuit.bend_90(
    BendRadius=.0762,
    ID = .022098,
    eps = eps,
    name = "bend1"
)

tube2 = circuit.tube_length(
    length = 1,
    ID = .022098,
    eps = eps,
    name = "tube_2"
)

valve1 = circuit.orifice(
    CdA = .000304024,
    Apt_Area = area
)

tube3 = circuit.tube_length(
    length = 1,
    ID = .022098,
    eps = eps,
    name = "tube_3"
)

bend2 = circuit.bend_90(
    BendRadius=.0762,
    ID = .022098,
    eps = eps,
    name = "bend2"
)

tube4 = circuit.tube_length(
    length = 1,
    ID = .022098,
    eps = eps,
    name = "tube_4"
)

hex = circuit.orifice(
    CdA = .000193278,
    Apt_Area = area,
    name = "HEX"
)

tube5 = circuit.tube_length(
    length = 1,
    ID = .022098,
    eps = eps,
    name = "tube_5"
)

syphon = circuit.syphon(
    syphon_flowrate = 0,
    syphon_area = 0.75,
    name = "RTT_intersection"
)

bend3 = circuit.bend_90(
    BendRadius=.0762,
    ID = .022098,
    eps = eps,
    name = "bend3"
)

tank_return_valve = circuit.orifice(
    CdA = .000304024,
    Apt_Area = area
)


summary = circuit.summary()

for key, value in summary.items():
    if key == "elements":
        continue
    if key == "fluid":
        print("fluid:")
        for subkey, subvalue in value.items():
            if subkey in {"state", "properties"}:
                continue
            print(f"  {subkey:18s}: {subvalue}")
    else:
        print(f"{key:20s}: {value}")

print(" ")
print(" ")
for i, element in enumerate(circuit.elements):
    print(
          f"{i:02d}. "
          f"type={element.element_type:12s} "
          f"name={str(element.name):18s} "
          f"dP={element.pressure_drop:12.3f} Pa"
      )
