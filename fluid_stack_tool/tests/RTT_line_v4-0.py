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


def in2m(value):
    return value * 0.0254


def in2m2(value):
    return value * 0.00064516


def format_sigfig(value):
    return f"{value:.3g}"

def FCV_function(percent_open):
    return -0.00000001*percent_open**4 + 0.000003*percent_open**3 - 0.0001*percent_open**2 + 0.0049*percent_open + 0.0001


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


def print_circuit_summary(circuit):
    # Pull a serializable snapshot of the final converged circuit state.
    summary = circuit.summary()
    pressure_keys = {"pressure", "dynamic_pressure", "static_pressure", "total_pressure_drop"}
    fluid_identity_keys = {"name", "temperature", "composition"}
    display_labels = {
        "dynamic_pressure": "dynamic q",
        "static_pressure": "static pressure",
        "total_pressure_drop": "signed dP sum",
        "flow_area": "flow area",
        "mdot": "mdot",
    }

    # Print the circuit-level summary first. Skip the element list here because
    # it is easier to read as a separate per-element table below.
    for key, value in summary.items():
        if key == "elements":
            continue
        if key == "fluid":
            print("fluid definition:")
            for subkey, subvalue in value.items():
                if subkey not in fluid_identity_keys:
                    continue
                print(f"  {subkey:18s}: {format_value(subvalue)}")
        else:
            label = display_labels.get(key, key)
            if key in pressure_keys:
                print_pressure_row(label, value)
            else:
                print(f"{label:20s}: {format_value(value)}")

    print(" ")


def plot_pump_dp_history(pump_dp_history):
    # Plot the bisection trial values when matplotlib is available.
    if plt is not None:
        plt.figure()
        plt.plot(range(1, len(pump_dp_history) + 1), pump_dp_history)
        plt.xlabel("Iteration")
        plt.ylabel("pump_dP")
        plt.title("pump_dP vs Iteration")
        plt.show()
    else:
        print("matplotlib not installed; skipping convergence plot.")


def iterator(fluid,pump_dp):
    # Build one full pass through the RTT return line using the current fluid
    # state as the circuit inlet condition.

    OD = in2m(1)
    wt = in2m(.065)
    ID = OD - 2*wt
    area_2in = 3.14* ID**2/4

    circuit = Circuit(
        fluid = fluid,
        mdot = 2,
    )

    LP_pump = circuit.pump(
        dP = 17/PA_TO_PSI, #17 psi. This is commensurate with the pump LP pump curve for 2 kg/s
        name = "LP_pump"
    )

    tube0 = circuit.tube_length(
        length = .5,
        ID = ID,
        eps = eps,
        name = "tube_0"
    )

    bend0 = circuit.bend_90(
        BendRadius=3*OD/2,
        ID = ID,
        eps = eps,
        name = "bend_0"
    )

    tube1 = circuit.tube_length(
        length = .5,
        ID = ID,
        eps = eps,
        name = "tube_1"
    )

    Boost_pump = circuit.pump(
        dP = pump_dp,
        name = "Boost_pump"
    )

    tube2 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_2"
    )

    bend1 = circuit.bend_90(
        BendRadius=3*OD/2,
        ID = ID,
        eps = eps,
        name = "bend_1"
    )

    tube3 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_3"
    )

    bend2 = circuit.bend_90(
        BendRadius=3*OD/2,
        ID = ID,
        eps = eps,
        name = "bend_2"
    )

    tube4 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_4"
    )

    hex = circuit.orifice(
        CdA = in2m2(0.41344667),
        Apt_Area = area_1in,
        name = "HEX"
    )

    tube5 = circuit.tube_length(
        length = 1,
        ID = ID,
        eps = eps,
        name = "tube_5"
    )

    syphon = circuit.syphon_main(
        syphon_flowrate = 0, # 0 indicates mode1, note that this is the flowrate flowing in the untracked branch
        syphon_area = .000484, #.75 in^2 #note that this is the area of the untracked branch
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

def main():
    # Bisection bounds for the pump head required to return to tank pressure.
    high =1e7
    low = 0
    tank_pressure =101352.9

    exit_pressure = 1
    i = 0
    pump_dp_history = []

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
        pump_dp_history.append(pump_dP)
        try:
            circuit = iterator(JP8,pump_dP)
        except:
            low = pump_dP
            pump_dP = (high+low)/2
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
        print(
            f"iteration {i:02d} | "
            f"pump_dP: {format_pressure(pump_dP)}"
        )

    print(" ")
    print(" ")
    print("Solved Pump dP")
    print(f"  {'Pump dP':18s}: {format_pressure(pump_dP)}")
    print(" ")
    print("Circuit Pressure Summary")
    print_pressure_row("circuit inlet", tank_pressure, indent="  ")
    print_pressure_row("circuit outlet", circuit.static_pressure, indent="  ")
    print_pressure_row("tank target", tank_pressure, indent="  ")
    print(" ")
    print(" ")
    print("Circuit Summary")
    print_circuit_summary(circuit)
    print_component_tally(
        build_pressure_tally(circuit, tank_pressure)
    )
    plot_pump_dp_history(pump_dp_history)

main()
