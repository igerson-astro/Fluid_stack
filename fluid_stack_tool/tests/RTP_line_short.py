from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fluid_stack import Fluid, Circuit


# Shared geometric inputs for the fixed line hardware.
area_1in = .0003835
eps = .015e-3

PA_TO_PSI = 0.00014503773773020923


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

def iterator(fluid,pump_dp):
    # Build one full pass through the RTT return line using the current fluid
    # state as the circuit inlet condition.

    OD = in2m(1)
    wt = in2m(.065)
    ID = OD - 2*wt
    area_2in = 3.14* ID**2/4

    circuit1_inlet_pressure = fluid.pressure
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
        Apt_Area = area_1in
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
    
    
    ############################### NEW CIRCUIT ################################################
    
    high =1e7
    low = 0
  
    circuit1_exit_pressure = circuit.static_pressure
    fluid2 = fluid
    i = 0
    RTP_pump_dp_history = []
    prop_inlet = 300/PA_TO_PSI #convert 300 psi to Pa
    wt = in2m(0.065)
    rtp_od = in2m(0.75)
    rtp_id = rtp_od - 2 * wt
    rtp_bend_radius = rtp_od * 3 / 2
    rtp_area = 3.14 * rtp_id**2 / 4

    
    for i in range(50):
        fluid2.pressure = circuit1_exit_pressure
        circuit_RTP = Circuit(
        fluid = fluid2,
        mdot = 1.44
        )

        Boost_dP = (high + low)/2
        RTP_pump_dp_history.append(Boost_dP)
        
        tube6 = circuit_RTP.tube_length(
            length = .2,
            ID = rtp_id,
            eps = eps,
            name = "tube_6"
        )

        bend3 = circuit_RTP.bend_90(
            BendRadius=rtp_bend_radius,
            ID = rtp_id,
            eps = eps,
            name = "RTP T-bend"
        )

        tube6 = circuit_RTP.tube_length(
            length = .1,
            ID = rtp_id,
            eps = eps,
            name = "tube_6"
        )

        bend4 = circuit_RTP.bend_90(
            BendRadius=rtp_bend_radius,
            ID = rtp_id,
            eps = eps,
            name = "RTP Bend2"
        )

        tube7 = circuit_RTP.tube_length(
            length = .1,
            ID = rtp_id,
            eps = eps,
            name = "tube_7"
        )

        Boost_pump = circuit_RTP.pump(
            dP = Boost_dP,
            name = "Boost_pump"
        )

        tube8 = circuit_RTP.tube_length(
            length = .1,
            ID = rtp_id,
            eps = eps,
            name = "tube_8"
        )

        Boost_iso = circuit_RTP.orifice(
            CdA = in2m2(.47),
            Apt_Area = rtp_area,
            name = "Boost_iso"
        )

        tube9 = circuit_RTP.tube_length(
            length = .2,
            ID = rtp_id,
            eps = eps,
            name = "tube_9"
        )

        Boundary_filter = circuit_RTP.orifice(
            CdA = in2m2(.47),
            Apt_Area = rtp_area,
            name = "Boundary_filter"
        )

        tube10 = circuit_RTP.tube_length(
            length = .1,
            ID = rtp_id,
            eps = eps,
            name = "tube_10"
        )

        bend5 = circuit_RTP.bend_90(
            BendRadius=rtp_bend_radius,
            ID = rtp_id,
            eps = eps,
            name = "Boundary Bend"
        )

        tube11 = circuit_RTP.tube_length(
            length = .1,
            ID = rtp_id,
            eps = eps,
            name = "boundary Tube"
        )



        if abs(circuit_RTP.static_pressure - prop_inlet)/prop_inlet <=1e-6:
            break
        elif circuit_RTP.static_pressure < prop_inlet:
            low = Boost_dP
        elif circuit_RTP.static_pressure > prop_inlet:
            high = Boost_dP

    pressure_report = {
        "circuit_1_inlet_pressure": circuit1_inlet_pressure,
        "circuit_1_outlet_pressure": circuit1_exit_pressure,
        "circuit_2_inlet_pressure": circuit1_exit_pressure,
        "circuit_2_outlet_pressure": circuit_RTP.static_pressure,
    }

    return circuit, circuit_RTP, Boost_dP, RTP_pump_dp_history, pressure_report


def printout(circuit,pump_dp_history):
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
    print(" ")
    # Print each circuit element in flow order so the stored dP values can be
    # compared directly against the circuit total.
    print("idx type         name                    dP")
    print("--  -----------  --------------------  ------------------------------------")
    for i, element in enumerate(circuit.elements):
        print(
            f"{i:02d}. "
            f"{element.element_type:11s}  "
            f"{str(element.name):20s}  "
            f"{format_pressure(element.pressure_drop)}"
        )

    # Plot the bisection trial values to visualize convergence.
    plt.plot(range(1, len(pump_dp_history) + 1), pump_dp_history)
    plt.xlabel("Iteration")
    plt.ylabel("pump_dP")
    plt.show()

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
        circuit, circuit_RTP, Boost_dP, RTP_Pump_dP_history, pressure_report = iterator(JP8,pump_dP)
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
            f"pump_dP: {format_pressure(pump_dP)} | "
            f"Boost_pump_dP: {format_pressure(Boost_dP)}"
        )

    print(" ")
    print(" ")
    print("Solved Pump dP")
    print(f"  {'pump1 dP':18s}: {format_pressure(pump_dP)}")
    print(f"  {'boost pump dP':18s}: {format_pressure(Boost_dP)}")
    print(" ")
    print("Circuit Pressure Summary")
    print_pressure_row("circuit 1 inlet", pressure_report["circuit_1_inlet_pressure"], indent="  ")
    print_pressure_row("circuit 1 outlet", pressure_report["circuit_1_outlet_pressure"], indent="  ")
    print_pressure_row("circuit 2 inlet", pressure_report["circuit_2_inlet_pressure"], indent="  ")
    print_pressure_row("circuit 2 outlet", pressure_report["circuit_2_outlet_pressure"], indent="  ")
    print(" ")
    print(" ")
    print(" ")
    print("---------------------Tank Section---------------------")
    printout(
        circuit=circuit,
        pump_dp_history=pump_dp_history
    )

    print(" ")
    print(" ")
    print(" ")
    print("---------------------RTP Section---------------------")
    printout(
        circuit=circuit_RTP,
        pump_dp_history=RTP_Pump_dP_history
    )


main()
