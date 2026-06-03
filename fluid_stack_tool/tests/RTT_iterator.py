from pathlib import Path
import sys

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit


# Shared geometric inputs for the fixed line hardware.
area_1in = .0003835
eps = .015e-3
PA_TO_PSI = 0.00014503773773020923
PRESSURE_COLUMN_WIDTH = 34


def format_sigfig(value):
    return f"{value:.3g}"


def format_pressure(value):
    pa = format_sigfig(value)
    psi = format_sigfig(value * PA_TO_PSI)
    return f"{pa:>10s} Pa | {psi:>10s} psi"


def build_pressure_tally(circuit, inlet_pressure):
    pressure_tally = []
    running_pressure = inlet_pressure

    for element in circuit.elements:
        inlet = running_pressure
        outlet = inlet - element.pressure_drop
        pressure_tally.append(
            {
                "type": element.element_type,
                "name": element.name,
                "pressure_drop": element.pressure_drop,
                "inlet_pressure": inlet,
                "outlet_pressure": outlet,
            }
        )
        running_pressure = outlet

    return pressure_tally


def print_major_component_tally(pressure_tally):
    major_types = {"pump", "orifice", "syphon"}

    print("Major Component Pressure Tally")
    print(
        f"{'idx':<4}"
        f"{'type':<13}"
        f"{'name':<22}"
        f"{'inlet pressure':<{PRESSURE_COLUMN_WIDTH}}"
        f"{'outlet pressure':<{PRESSURE_COLUMN_WIDTH}}"
        f"{'dP':<{PRESSURE_COLUMN_WIDTH}}"
    )
    print(
        f"{'--':<4}"
        f"{'-' * 11:<13}"
        f"{'-' * 20:<22}"
        f"{'-' * (PRESSURE_COLUMN_WIDTH - 2):<{PRESSURE_COLUMN_WIDTH}}"
        f"{'-' * (PRESSURE_COLUMN_WIDTH - 2):<{PRESSURE_COLUMN_WIDTH}}"
        f"{'-' * (PRESSURE_COLUMN_WIDTH - 2):<{PRESSURE_COLUMN_WIDTH}}"
    )

    for i, row in enumerate(pressure_tally):
        if row["type"] not in major_types:
            continue
        print(
            f"{f'{i:02d}.':<4}"
            f"{row['type']:<13}"
            f"{str(row['name']):<22}"
            f"{format_pressure(row['inlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['outlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['pressure_drop']):<{PRESSURE_COLUMN_WIDTH}}"
        )

    print(" ")

def iterator(fluid,pump_dp,flowrate):
    # Build one full pass through the RTT return line using the current fluid
    # state as the circuit inlet condition.
    circuit = Circuit(
        fluid = fluid,
        mdot = flowrate,
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
        Apt_Area = area_1in,
        name = "line_valve"
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
    # CdA for 10 psi HEX
    # hex = circuit.orifice(
    #     CdA = .000193278,
    #     Apt_Area = area_1in,
    #     name = "HEX"
    # )
    #CdA for 5 psi HEX
    hex = circuit.orifice(
        CdA = 0.000266739,
        Apt_Area = area_1in,
        name = "HEX"
    )

    tube5 = circuit.tube_length(
        length = 1,
        ID = .022098,
        eps = eps,
        name = "tube_5"
    )

    syphon = circuit.syphon_main(
        syphon_flowrate = 0,
        syphon_area = .000484, #.75 in^2
        name = "RTT_intersection"
    )

    bend3 = circuit.bend_90(
        BendRadius=.0762,
        ID = .022098,
        eps = eps,
        name = "bend3"
    )

    tank_return_valve = circuit.orifice(
        CdA = .00049,
        Apt_Area = area_1in,
        name = "tank_return_valve"
    )

    return circuit

def iterator_engine(tank_pressure, flowrate):
    i=0
    exit_pressure = 1
    # Bisection bounds for the pump head required to return to tank pressure.
    high =1e7
    low = 0
    while abs(exit_pressure-tank_pressure)/tank_pressure > 1e-6 and i < 50:
        # Circuit now takes its starting pressure from fluid.pressure, and the
        # circuit march updates that pressure in place. Rebuild the fluid each
        # iteration so every trial starts from the same tank condition.
        JP8 = Fluid(
        name = "JP8.mix",
        temperature = 278.15,
        pressure = tank_pressure
        )

        # Midpoint trial for the current bisection bracket.
        pump_dP = (high+low)/2
        circuit = iterator(JP8,pump_dP,flowrate)
        # The outlet static pressure is the value we are matching to the tank.
        exit_pressure = circuit.static_pressure

        # Standard bisection update: if outlet is too low, increase pump dP;
        # if outlet is too high, decrease it.
        if exit_pressure < tank_pressure:
            low = pump_dP
        elif exit_pressure > tank_pressure:
            high = pump_dP
        
        i+=1
    if i==50:
        return 0
    else:
        return pump_dP

def main():
    
    tank_pressure =101352.9

    
    i = 0
    pump_dp_history = []
    flowrates = [.5,.75,1,1.25,1.5,1.75,2]
    pump_output =[]
    for mdot in flowrates:
        pump_output.append(iterator_engine(tank_pressure=tank_pressure,flowrate=mdot))


    for i in range(len(flowrates)):
        i
        print(f"{flowrates[i]}:  {pump_output[i]/1e6}")
    
        
        
main()
