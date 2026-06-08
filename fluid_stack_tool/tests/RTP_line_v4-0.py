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
PROP_INLET_TARGET = 300 / PA_TO_PSI #convert 300 psi to Pa


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


def build_combined_pressure_tally(circuits_and_inlets):
    pressure_tally = []

    for circuit, inlet_pressure in circuits_and_inlets:
        pressure_tally.extend(build_pressure_tally(circuit, inlet_pressure))

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


def iterator(fluid, Boost_pump_dp):
    # Build one full pass through the RTT return line using the current fluid
    # state as the circuit inlet condition.

    OD = in2m(1)
    wt = in2m(.065)
    ID = OD - 2*wt
    area_2in = 3.14* ID**2/4

    circuit_inlet_pressure = fluid.pressure
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
        dP = Boost_pump_dp,
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
    
    wt = in2m(0.065)
    rtp_od = in2m(0.75)
    rtp_id = rtp_od - 2 * wt
    rtp_bend_radius = rtp_od * 3 / 2
    rtp_area = 3.14 * rtp_id**2 / 4

    syphon = circuit.syphon_branch(
        branch_flowrate = 1.44,
        initial_flowrate= 2,
        main_area = area_1in, 
        branch_radius =0, # worst possible case
        branch_ID = rtp_id,
        name = "RTP_intersection"
    )

    tube6 = circuit.tube_length(
        length = .2,
        ID = rtp_id,
        eps = eps,
        name = "tube_6"
    )

    bend3 = circuit.bend_90(
        BendRadius=rtp_bend_radius,
        ID = rtp_id,
        eps = eps,
        name = "bend_3"
    )

    tube7 = circuit.tube_length(
        length = .1,
        ID = rtp_id,
        eps = eps,
        name = "tube_7"
    )

    bend4 = circuit.bend_90(
        BendRadius=rtp_bend_radius,
        ID = rtp_id,
        eps = eps,
        name = "bend_4"
    )

    tube8 = circuit.tube_length(
        length = .2,
        ID = rtp_id,
        eps = eps,
        name = "tube_8"
    )

    Prop_iso = circuit.orifice(
        CdA = in2m2(.47),
        Apt_Area = rtp_area,
        name = "prop_iso"
    )

    tube9 = circuit.tube_length(
        length = .2,
        ID = rtp_id,
        eps = eps,
        name = "tube_9"
    )

    Boundary_filter = circuit.orifice(
        CdA = in2m2(.47),
        Apt_Area = rtp_area,
        name = "Boundary_filter"
    )

    tube10 = circuit.tube_length(
        length = .1,
        ID = rtp_id,
        eps = eps,
        name = "tube_10"
    )

    bend5 = circuit.bend_90(
        BendRadius=rtp_bend_radius,
        ID = rtp_id,
        eps = eps,
        name = "bend_5"
    )

    tube11 = circuit.tube_length(
        length = .1,
        ID = rtp_id,
        eps = eps,
        name = "tube_11"
    )

    pressure_report = {
        "circuit_1_inlet_pressure": circuit_inlet_pressure,
        "circuit_2_outlet_pressure": circuit.static_pressure,
        "prop_inlet_target_pressure": PROP_INLET_TARGET,
    }

    return circuit, circuit, pressure_report


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


def plot_Boost_pump_dp_history(Boost_pump_dp_history):
    # Plot the bisection trial values to visualize convergence.
    plt.figure()
    plt.plot(range(1, len(Boost_pump_dp_history) + 1), Boost_pump_dp_history)
    plt.xlabel("Iteration")
    plt.ylabel("Boost_pump_dP")
    plt.title("Boost_pump_dP vs Iteration")
    plt.show()

def main():
    # Bisection bounds for the boost pump head required to hit prop inlet pressure.
    high =1e7
    low = 0
    tank_pressure =1.65/PA_TO_PSI
    #tank_pressure = .0114e6
    exit_pressure = 0
    i = 0
    Boost_pump_dp_history = []

    while abs(exit_pressure-PROP_INLET_TARGET)/PROP_INLET_TARGET > 1e-6 and i < 50:
        # Circuit now takes its starting pressure from fluid.pressure, and the
        # circuit march updates that pressure in place. Rebuild the fluid each
        # iteration so every trial starts from the same tank condition.
        JP8 = Fluid(
        name = "JP8.mix",
        temperature = 353.15,
        pressure = tank_pressure
        )

        # Midpoint trial for the current bisection bracket.
        Boost_pump_dp = (high+low)/2
        Boost_pump_dp_history.append(Boost_pump_dp)
        try:
            circuit, circuit_RTP, pressure_report = iterator(JP8, Boost_pump_dp)
            # The RTP outlet static pressure is the value matched to prop inlet.
            exit_pressure = circuit_RTP.static_pressure
        except ValueError as exc:
            # Very low boost trials can make the RTP pressure nonphysical before
            # the outlet is reached. Treat those trials as below the target.
            low = Boost_pump_dp
            exit_pressure = 0
            i += 1
            print(
                f"iteration {i:02d} | "
                f"Boost_pump_dP: {format_pressure(Boost_pump_dp)} | "
                f"RTP outlet below valid REFPROP pressure ({exc})"
            )
            continue

        # Standard bisection update: if RTP outlet is too low, increase boost
        # pump dP; if outlet is too high, decrease it.
        if exit_pressure < PROP_INLET_TARGET:
            low = Boost_pump_dp
        elif exit_pressure > PROP_INLET_TARGET:
            high = Boost_pump_dp
        
        i += 1
        print(
            f"iteration {i:02d} | "
            f"Boost_pump_dP: {format_pressure(Boost_pump_dp)}"
        )

    print(" ")
    print(" ")
    print("Solved Boost Pump dP")
    print(f"  {'Boost pump dP':18s}: {format_pressure(Boost_pump_dp)}")
    print(" ")
    print("Circuit Pressure Summary")
    print_pressure_row("circuit inlet", pressure_report["circuit_1_inlet_pressure"], indent="  ")
    print_pressure_row("circuit outlet", pressure_report["circuit_2_outlet_pressure"], indent="  ")
    print_pressure_row("prop target", pressure_report["prop_inlet_target_pressure"], indent="  ")
    print(" ")
    print(" ")
    print("Circuit Summary")
    print_circuit_summary(circuit)
    print_component_tally(
        build_pressure_tally(circuit, pressure_report["circuit_1_inlet_pressure"])
    )
    plot_Boost_pump_dp_history(Boost_pump_dp_history)


main()
