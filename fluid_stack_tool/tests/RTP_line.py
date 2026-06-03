from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit


# Shared geometric inputs for the fixed line hardware.
area_1in = .0003835 #m^2
area_75in = 0.000285023 #m^2
ID_75in = .0157
eps = .015e-3
fluid = "JP8.mix"
#LP_pump_dP = 0.21e6
LP_pump_dP = .27e6
Boost_pump_dp=2.5e6 #Pa
prop_flowrate = 1.44 #kg/s
tank_pressure =.101e6

JP8 = Fluid(
        name = "JP8.mix",
        temperature = 323.15,
        pressure = tank_pressure
        )

circuit = Circuit(
    fluid = JP8,
    mdot = 2,
)

LP_pump = circuit.pump(
    dP = LP_pump_dP,
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
    Apt_Area = area_1in
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
    Apt_Area = area_1in,
    name = "HEX"
)

tube5 = circuit.tube_length(
    length = 1,
    ID = .022098,
    eps = eps,
    name = "tube_5"
)

syphon = circuit.syphon_branch(
        branch_flowrate = 1.4,
        initial_flowrate= 2,
        main_area = area_1in, 
        branch_radius =0, # worst possible case
        branch_ID = ID_75in,
        name = "RTP_intersection"
)

tube6 = circuit.tube_length(
    length = .5,
    ID = ID_75in,
    eps = eps,
    name = "tube_6"
)

bend3 = circuit.bend_90(
    BendRadius = .2286, #3x .75 in radius converted to m
    ID = ID_75in,
    eps = eps,
    name = "bend3"
)

tube6 = circuit.tube_length(
    length = 1,
    ID = ID_75in,
    eps = eps,
    name = "tube_6"
)

LP_pump = circuit.pump(
    dP = Boost_pump_dp,
    name = "LP_pump"
)

tube7 = circuit.tube_length(
    length = .5,
    ID = ID_75in,
    eps = eps,
    name = "tube_7"
)

valve2 = circuit.orifice(
    CdA = .000304024,
    Apt_Area = area_75in,
    name = "boost_pump_iso"
)

tube8 = circuit.tube_length(
    length = .5,
    ID = ID_75in,
    eps = eps,
    name = "tube_8"
)

filter = circuit.orifice(
    CdA = .000197,
    Apt_Area = area_75in,
    name = "boundary_filter"
)

tube9 = circuit.tube_length(
    length = .5,
    ID = ID_75in,
    eps = eps,
    name = "tube_9"
)

# Pull a serializable snapshot of the final converged circuit state.
summary = circuit.summary()

# Print the circuit-level summary first. Skip the element list here because
# it is easier to read as a separate per-element table below.
for key, value in summary.items():
    if key == "elements":
        continue
    if key == "fluid":
        # The fluid entry is itself a nested dictionary. Print the high-level
        # fields and skip the raw state/properties sub-dicts to keep the
        # report compact.
        print("fluid:")
        for subkey, subvalue in value.items():
            if subkey in {"state", "properties"}:
                continue
            print(f"  {subkey:18s}: {subvalue}")
    else:
        print(f"{key:20s}: {value}")

print(" ")
print(" ")
# Print each circuit element in flow order so the stored dP values can be
# compared directly against the circuit total.
for i, element in enumerate(circuit.elements):
    print(
        f"{i:02d}. "
        f"type={element.element_type:12s} "
        f"name={str(element.name):18s} "
        f"dP={element.pressure_drop:12.3f} Pa"
    )
