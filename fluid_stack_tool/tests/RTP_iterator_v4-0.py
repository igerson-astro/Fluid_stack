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


def m2in(value):
    return value / 0.0254


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
                "ID": getattr(element, "ID", None),
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


def print_component_tally(pressure_tally):
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

    for row in pressure_tally:
        print(
            f"{f'{row['idx']:02d}.':<4}"
            f"{row['type']:<{TYPE_COLUMN_WIDTH}}"
            f"{str(row['name']):<22}"
            f"{format_pressure(row['inlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['outlet_pressure']):<{PRESSURE_COLUMN_WIDTH}}"
            f"{format_pressure(row['pressure_drop']):<{PRESSURE_COLUMN_WIDTH}}"
        )

    print(" ")


def bucket_pressure_source(row):
    if row["type"] == "tube_length":
        diameter = row["ID"]
        if diameter is None:
            return "tubes unknown ID"
        return f"tubes {format_sigfig(m2in(diameter))} in ID"

    if row["type"] in {"bend_90", "bend_45"}:
        diameter = row["ID"]
        if diameter is None:
            return "bends unknown ID"
        return f"bends {format_sigfig(m2in(diameter))} in ID"

    return str(row["name"] or row["type"])


def build_dp_buckets(circuit, inlet_pressure):
    buckets = {}
    bucket_counts = {}
    bucket_lengths = {}

    for element in circuit.elements:
        if element.element_type == "pump":
            continue

        row = {
            "type": element.element_type,
            "name": element.name,
            "ID": getattr(element, "ID", None),
        }
        bucket = bucket_pressure_source(row)
        buckets[bucket] = buckets.get(bucket, 0.0) + abs(element.pressure_drop)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if element.element_type == "tube_length":
            bucket_lengths[bucket] = bucket_lengths.get(bucket, 0.0) + element.length

    return buckets, bucket_counts, bucket_lengths


def plot_dp_histogram(flowrate, circuit, inlet_pressure):
    if plt is None:
        print("matplotlib not installed; skipping dP source histogram.")
        return

    if circuit is None:
        print("No converged component dP data available; skipping dP source histogram.")
        return

    buckets, bucket_counts, bucket_lengths = build_dp_buckets(circuit, inlet_pressure)
    if not buckets:
        print("No non-pump component dP data available; skipping dP source histogram.")
        return

    bucket_names = sorted(
        buckets,
        key=lambda bucket: buckets[bucket],
    )
    values = [buckets[bucket] * PA_TO_PSI for bucket in bucket_names]

    plt.figure(figsize=(10, 5))
    bars = plt.barh(bucket_names, values, color="tab:green")
    max_value = max(values)
    plt.xlim(0, max_value * 1.12)
    for bar, bucket in zip(bars, bucket_names):
        if bucket.startswith("tubes "):
            label = f"{format_sigfig(bucket_lengths[bucket])} m"
        else:
            count = bucket_counts[bucket]
            label = f"{count}x"
        plt.text(
            bar.get_width() + max_value * 0.015,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=13,
        )

    plt.xlabel("Pressure drop, psi", fontsize=14, fontweight="bold")
    plt.ylabel("Pressure drop element", fontsize=14, fontweight="bold")
    plt.title(f"RTP dP Sources at {format_sigfig(flowrate)} kg/s", fontsize=18, fontweight="bold")
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=13)
    plt.tight_layout()

    output_path = Path(__file__).with_name("RTP_iterator_v4-0_dp_histogram.png")
    plt.savefig(output_path, dpi=200)

    if "agg" in plt.get_backend().lower():
        print(f"dP source histogram saved to {output_path}")
        return

    plt.show()


def iterator(fluid, pump_dp, flowrate):
    # Build one full pass through the RTP line using the current fluid
    # state as the circuit inlet condition.

    OD = in2m(2)
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

    LP_pump_iso_valve = circuit.orifice(
        CdA = in2m(0.76),
        Apt_Area = area_1in,
        name = "LP_pump_iso-valve"
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
    rtp_od = in2m(.75)
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
        temperature = 353.15,
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

    for flowrate, circuit in zip(flowrates, solved_circuits):
        if circuit is None:
            print(" ")
            print(f"Flowrate: {flowrate}")
            print("No converged circuit available.")
            continue

        print(" ")
        print(f"Flowrate: {flowrate}")
        print_component_tally(
            build_pressure_tally(circuit, tank_pressure)
        )

    print(" ")
    for i in range(len(flowrates)):
        i
        print(f"{flowrates[i]}:  {pump_output[i]/1e6}   ")

    plot_dp_histogram(flowrates[-1], solved_circuits[-1], tank_pressure)
    
        
        
main()
