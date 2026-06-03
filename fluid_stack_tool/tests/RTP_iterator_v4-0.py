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
TYPE_COLUMN_WIDTH = 15
BOOST_INLET_TARGET = 8 / PA_TO_PSI #convert 8 psi to Pa


def in2m(value):
    return value * 0.0254


def in2m2(value):
    return value * 0.00064516


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
                "idx": len(pressure_tally),
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
    major_types = {"pump", "orifice", "syphon branch"}

    print("Major Component Pressure Tally")
    print(
        f"{'idx':<4}"
        f"{'type':<{TYPE_COLUMN_WIDTH}}"
        f"{'name':<22}"
        f"{'inlet pressure':<{PRESSURE_COLUMN_WIDTH}}"
        f"{'outlet pressure':<{PRESSURE_COLUMN_WIDTH}}"
        f"{'dP':<{PRESSURE_COLUMN_WIDTH}}"
    )
    print(
        f"{'--':<4}"
        f"{'-' * (TYPE_COLUMN_WIDTH - 2):<{TYPE_COLUMN_WIDTH}}"
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
            f"{row['type']:<{TYPE_COLUMN_WIDTH}}"
            f"{str(row['name']):<22}"
            f"{format_pressure(row['inlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['outlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['pressure_drop']):<{PRESSURE_COLUMN_WIDTH}}"
        )

    print(" ")


def print_component_tally_by_largest_dp(pressure_tally):
    largest_rows = sorted(
        pressure_tally,
        key=lambda row: abs(row["pressure_drop"]),
        reverse=True,
    )

    print("Component Pressure Tally")
    print(
        f"{'idx':<4}"
        f"{'type':<{TYPE_COLUMN_WIDTH}}"
        f"{'name':<22}"
        f"{'inlet pressure':<{PRESSURE_COLUMN_WIDTH}}"
        f"{'outlet pressure':<{PRESSURE_COLUMN_WIDTH}}"
        f"{'dP':<{PRESSURE_COLUMN_WIDTH}}"
    )
    print(
        f"{'--':<4}"
        f"{'-' * (TYPE_COLUMN_WIDTH - 2):<{TYPE_COLUMN_WIDTH}}"
        f"{'-' * 20:<22}"
        f"{'-' * (PRESSURE_COLUMN_WIDTH - 2):<{PRESSURE_COLUMN_WIDTH}}"
        f"{'-' * (PRESSURE_COLUMN_WIDTH - 2):<{PRESSURE_COLUMN_WIDTH}}"
        f"{'-' * (PRESSURE_COLUMN_WIDTH - 2):<{PRESSURE_COLUMN_WIDTH}}"
    )

    for row in largest_rows:
        print(
            f"{f'{row['idx']:02d}.':<4}"
            f"{row['type']:<{TYPE_COLUMN_WIDTH}}"
            f"{str(row['name']):<22}"
            f"{format_pressure(row['inlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['outlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['pressure_drop']):<{PRESSURE_COLUMN_WIDTH}}"
        )

    print(" ")


def iterator(fluid, pump_dp, flowrate):
    # Build one full pass through the RTP line using the current fluid
    # state as the circuit inlet condition.

    OD = in2m(1)
    wt = in2m(.065)
    ID = OD - 2*wt
    area_2in = 3.14* ID**2/4

    circuit = Circuit(
        fluid = fluid,
        mdot = flowrate,
    )

    LP_pump = circuit.pump(
        dP = pump_dp,
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
        branch_flowrate = 1.44/2*flowrate,
        initial_flowrate = flowrate,
        main_area = area_1in, 
        branch_radius = 0, # worst possible case
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

    # tube7 = circuit.tube_length(
    #     length = .1,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "tube_7"
    # )

    # bend4 = circuit.bend_90(
    #     BendRadius=rtp_bend_radius,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "bend_4"
    # )

    # tube8 = circuit.tube_length(
    #     length = .2,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "tube_8"
    # )

    # Prop_iso = circuit.orifice(
    #     CdA = in2m2(.47),
    #     Apt_Area = rtp_area,
    #     name = "prop_iso"
    # )

    # tube9 = circuit.tube_length(
    #     length = .2,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "tube_9"
    # )

    # Boundary_filter = circuit.orifice(
    #     CdA = in2m2(.47),
    #     Apt_Area = rtp_area,
    #     name = "Boundary_filter"
    # )

    # tube10 = circuit.tube_length(
    #     length = .1,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "tube_10"
    # )

    # bend5 = circuit.bend_90(
    #     BendRadius=rtp_bend_radius,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "bend_5"
    # )

    # tube11 = circuit.tube_length(
    #     length = .1,
    #     ID = rtp_id,
    #     eps = eps,
    #     name = "tube_11"
    # )

    return circuit


def iterator_engine(tank_pressure, flowrate):
    i=0
    exit_pressure = 1
    # Bisection bounds for the pump head required to hit prop inlet pressure.
    high =1e7
    low = 0
    while abs(exit_pressure-BOOST_INLET_TARGET)/BOOST_INLET_TARGET > 1e-6 and i < 50:
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
        try:
            circuit = iterator(JP8,pump_dP,flowrate)
            # The outlet static pressure is the value matched to prop inlet.
            exit_pressure = circuit.static_pressure
        except ValueError:
            low = pump_dP
            exit_pressure = 0
            i += 1
            continue

        # Standard bisection update: if outlet is too low, increase pump dP;
        # if outlet is too high, decrease it.
        if exit_pressure < BOOST_INLET_TARGET:
            low = pump_dP
        elif exit_pressure > BOOST_INLET_TARGET:
            high = pump_dP
        
        i+=1
    if i==50:
        return 0, 0, None
    else:
        return pump_dP, circuit.total_pressure_drop, circuit


def main():
    
    #tank_pressure =110084.8992
    tank_pressure =1.65/PA_TO_PSI 


    
    i = 0
    pump_dp_history = []
    flowrates = [.5,.75,1,1.25,1.5,1.75,2]
    pump_output =[]
    total_dP = []
    solved_circuits = []
    for mdot in flowrates:
        pump_dp, circuit_dp, circuit = iterator_engine(tank_pressure=tank_pressure,flowrate=mdot)
        pump_output.append(pump_dp)
        total_dP.append(circuit_dp)
        solved_circuits.append(circuit)


    for i in range(len(flowrates)):
        i
        print(f"{flowrates[i]}:  {pump_output[i]/1e6}   ")

    for flowrate, circuit in zip(flowrates, solved_circuits):
        if circuit is None:
            print(" ")
            print(f"Flowrate: {flowrate}")
            print("No converged circuit available.")
            continue

        print(" ")
        print(f"Flowrate: {flowrate}")
        print_component_tally_by_largest_dp(
            build_pressure_tally(circuit, tank_pressure)
        )
    
        
        
main()
