from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit


# Shared geometric inputs for the fixed line hardware.
area = .0003835
eps = .015e-3

def iterator(fluid,pump_dp):
    # Build one full pass through the RTT return line using the current fluid
    # state as the circuit inlet condition.
    circuit = Circuit(
        fluid = fluid,
        mdot = 2,
    )

    LP_pump = circuit.pump(
        dP = pump_dp,
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

    return circuit

def main():
    # Bisection bounds for the pump head required to return to tank pressure.
    high =1e7
    low = 0
    tank_pressure =.101e6
    exit_pressure = 1
    i = 0
    pump_dp_history = []

    while abs(exit_pressure-tank_pressure)/tank_pressure > 1e-6 and i < 50:
        # Circuit now takes its starting pressure from fluid.pressure, and the
        # circuit march updates that pressure in place. Rebuild the fluid each
        # iteration so every trial starts from the same tank condition.
        JP8 = Fluid(
        name = "JP8.mix",
        temperature = 323.15,
        pressure = tank_pressure
        )

        # Midpoint trial for the current bisection bracket.
        pump_dP = (high+low)/2
        pump_dp_history.append(pump_dP)
        circuit = iterator(JP8,pump_dP)
        # The outlet static pressure is the value we are matching to the tank.
        exit_pressure = circuit.static_pressure

        # Standard bisection update: if outlet is too low, increase pump dP;
        # if outlet is too high, decrease it.
        if exit_pressure < tank_pressure:
            low = pump_dP
        elif exit_pressure > tank_pressure:
            high = pump_dP
        
        i += 1
        print(f"iteration {i}: pump_dP = {pump_dP}")

    print(" ")
    print(" ")
    print(f" FOUND PUMP dP:   {pump_dP*1e-6}")
    print(" ")
    print(" ")
    print(" ")

    

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

    # Plot the bisection trial values to visualize convergence.
    plt.plot(range(1, len(pump_dp_history) + 1), pump_dp_history)
    plt.xlabel("Iteration")
    plt.ylabel("pump_dP")
    plt.show()

main()
