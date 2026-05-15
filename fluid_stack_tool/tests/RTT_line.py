from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit

#pressure = .101e6
area = .0003835
eps = .015e-3

def iterator(fluid,tank_pressure,pump_dp):

    
    circuit = Circuit(
        fluid = fluid,
        mdot = 2,
        static_pressure = tank_pressure
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
    high =1e7
    low = 0
    tank_pressure =.7e6
    exit_pressure = 1
    i = 0
    pump_dp_history = []

    JP8 = Fluid(
        name = "JP8.mix",
        temperature = 323.15,
        pressure = tank_pressure
    )
    
    while abs(exit_pressure-tank_pressure)/tank_pressure > 1e-5 and i < 50:
        if i == 4:
            print(i)
        pump_dP = (high+low)/2
        pump_dp_history.append(pump_dP)
        circuit = iterator(JP8,tank_pressure,pump_dP)
        exit_pressure = circuit.static_pressure

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

    plt.plot(range(1, len(pump_dp_history) + 1), pump_dp_history)
    plt.xlabel("Iteration")
    plt.ylabel("pump_dP")
    #plt.show()

main()
