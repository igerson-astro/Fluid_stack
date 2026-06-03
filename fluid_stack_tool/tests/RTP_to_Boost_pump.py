from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit


# Shared geometric inputs for the fixed line hardware.
area_1in = .0003835
eps = .015e-3

PA_TO_PSI = 0.00014503773773020923
PRESSURE_COLUMN_WIDTH = 34


def in2m(value):
    return value * 0.0254

def in2m2(value):
    return value * 0.00064516


def format_sigfig(value):
    return f"{value:.3g}"


def format_value(value):
    if isinstance(value, float):
        return format_sigfig(value)
    if isinstance(value, list):
        return "[" + ", ".join(format_value(item) for item in value) + "]"
    if isinstance(value, tuple):
        return "(" + ", ".join(format_value(item) for item in value) + ")"
    return str(value)


def format_pressure(value):
    pa = format_sigfig(value)
    psi = format_sigfig(value * PA_TO_PSI)
    return f"{pa:>10s} Pa | {psi:>10s} psi"


def print_pressure_row(label, value, indent=""):
    print(f"{indent}{label:18s}: {format_pressure(value)}")


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


def print_component_tally(pressure_tally):
    print("Component Pressure Tally")
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
        print(
            f"{f'{i:02d}.':<4}"
            f"{row['type']:<13}"
            f"{str(row['name']):<22}"
            f"{format_pressure(row['inlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['outlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['pressure_drop']):<{PRESSURE_COLUMN_WIDTH}}"
        )

    print(" ")

def iterator(fluid,pump_dp):
    # Build one full pass through the RTT return line using the current fluid
    # state as the circuit inlet condition.

    OD = in2m(1)
    wt = in2m(.065)
    ID = OD - 2*wt
    area_2in = 3.14* ID**2/4

    inlet_pressure = fluid.pressure
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
        ID = ID,
        eps = eps,
        name = "tube_1"
    )

    bend1 = circuit.bend_90(
        BendRadius=.0762,
        ID = ID,
        eps = eps,
        name = "bend1"
    )

    tube2 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_2"
    )

    valve1 = circuit.orifice(
        CdA = in2m2(.47),
        Apt_Area = area_1in,
        name = "line_valve"
    )

    tube3 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_3"
    )

    bend2 = circuit.bend_90(
        BendRadius=.0762,
        ID = ID,
        eps = eps,
        name = "bend2"
    )

    tube4 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_4"
    )

    hex = circuit.orifice(
        CdA = in2m2(.3),
        Apt_Area = area_1in,
        name = "HEX"
    )

    tube5 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_5"
    )    

    return circuit

def main():
    fluid_name = "JP8.mix"
    temperature = 353.15  # K
    inlet_pressure = 0.012e6  # Pa
    goal = 0.055e6  # Pa

    high = 5e7  # Pa
    low = 3e3  # Pa
    dP_history = []
    i_history =[]
    for i in range(50):
        fluid = Fluid(
            name=fluid_name,
            temperature=temperature,
            pressure=inlet_pressure,
        )
        pump_dP = (high + low)/2
        dP_history.append(pump_dP)
        i_history.append(i)
        circuit = iterator(
            fluid=fluid,
            pump_dp=pump_dP
        )
        boost_NPSP = circuit.static_pressure

        if abs(boost_NPSP - goal)/boost_NPSP <= .00001:
            print( f"COMPLETE - MIN dP = {pump_dP}")
            print(" ")
            print_component_tally(build_pressure_tally(circuit, inlet_pressure))
            plt.plot(i_history,dP_history)
            plt.show()
            return
        elif boost_NPSP > goal:
            high = pump_dP
        else:
            low = pump_dP

main()
