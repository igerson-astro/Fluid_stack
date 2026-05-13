# fluid_stack

`fluid_stack` is a Python library for estimating pressure changes through a fluid circuit made of pumps and resistive elements.

The current design is circuit-driven:
- You create a `Fluid`
- You create a `Circuit`
- You add elements to the circuit in flow order
- Each element calculates its own pressure effect when it is added
- The circuit updates fluid state after each element

All units are assumed to be SI.

## Requirements

- Python environment with `ctREFPROP` installed
- A working REFPROP installation
- `RPPREFIX` environment variable pointing to the REFPROP directory

`core.py` initializes REFPROP directly with:

```python
from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary
```

and uses REFPROP for all fluid state calls.

## Main Objects

### `Fluid`

`Fluid` stores the thermodynamic and flow state associated with the circuit fluid.

Constructor:

```python
Fluid(
    name: str,
    temperature: float,
    pressure: float | None = None,
    composition: list[float] | None = None,
    **properties,
)
```

Important stored values:
- `name`: REFPROP fluid name, for example `"WATER"` or `"JP8.mix"`
- `temperature`: fluid temperature in K
- `pressure`: current static pressure in Pa
- `state["density"]`: current density from REFPROP
- `state["viscosity"]`: current viscosity from REFPROP
- `reynolds_number`: current Reynolds number for the active element
- `dynamic_pressure`: current `0.5 * rho * v^2`

Major methods:
- `calculate_state(...)`
  - Calls REFPROP and returns density and viscosity at the requested `T, P`
- `update_state(...)`
  - Calls `calculate_state(...)` and stores the result on the object
- `calculate_density(...)`
  - Convenience wrapper for density only
- `calculate_viscosity(...)`
  - Convenience wrapper for viscosity only
- `update_reynolds_number(...)`
  - Stores the current Reynolds number from `rho`, `v`, `D`, and `mu`
- `update_dynamic_pressure(...)`
  - Stores the current dynamic pressure from `rho` and `v`
- `summary()`
  - Returns a serializable dictionary view of the current fluid state

### `Circuit`

`Circuit` owns the ordered list of elements and updates the hydraulic state as each new element is added.

Constructor:

```python
Circuit(
    fluid: Fluid,
    mdot: float | None = None,
    static_pressure: float | None = None,
    flow_area: float | None = None,
)
```

Inputs:
- `fluid`: the `Fluid` instance used throughout the circuit
- `mdot`: mass flow rate through the circuit
- `static_pressure`: starting line pressure
- `flow_area`: optional starting area if you need the circuit to derive velocity before the first element defines an area

Important stored values:
- `elements`: ordered list of circuit elements
- `total_pressure_drop`: signed running sum of all element pressure effects
- `static_pressure`: current line pressure after each element
- `density`: current fluid density
- `viscosity`: current fluid viscosity
- `velocity`: current bulk velocity derived from `mdot / (rho * A)`
- `flow_area`: current reference area

Major methods:
- `orifice(...)`
- `pump(...)`
- `tube_length(...)`
- `bend_90(...)`
- `bend_45(...)`
- `summary()`

Each add-method:
1. Instantiates the element
2. Attaches it to the circuit
3. Updates flow kinematics for that element area
4. Updates fluid Reynolds number for non-pump elements
5. Calculates and stores the element pressure drop
6. Appends the element to `circuit.elements`
7. Adds the element contribution into `total_pressure_drop`
8. Updates static pressure
9. Re-queries REFPROP at the new pressure

### `CircuitElement`

`CircuitElement` is the base class for pumps and resistors.

Important methods:
- `calculate_pressure_drop(...)`
  - Shared default implementation for K-based elements
- `update_pressure_drop(...)`
  - Calculates and stores `pressure_drop`
- `summary()`

The default pressure-drop model is:

```python
dP = dynamic_pressure * K
```

For K-based elements, `dynamic_pressure` is read from the owning `Fluid`.

## Supported Elements

### `Pump`

Constructor:

```python
Pump(dP: float, **kwargs)
```

Behavior:
- Returns `-dP`
- A negative stored pressure drop is used to represent a pressure gain

### `Orifice`

Constructor:

```python
Orifice(CdA: float, Apt_Area: float, **kwargs)
```

Stored values:
- `CdA`
- `Apt_Area`
- `Cd = CdA / Apt_Area`

Major method:
- `calc_K()`
  - Converts the orifice definition into an equivalent loss coefficient

### `TubeLength`

Constructor:

```python
TubeLength(length: float, ID: float, eps: float, **kwargs)
```

Stored values:
- `length`
- `ID`
- `eps`
- `Area`
- `f` after solution

Major method:
- `calc_K()`
  - Solves Darcy friction factor using the Colebrook equation
  - Returns straight-pipe loss in K-factor form

### `Bend90`

Constructor:

```python
Bend90(BendRadius: float, ID: float, eps: float, **kwargs)
```

Major methods:
- `calc_alpha()`
- `calc_K()`

### `Bend45`

Constructor:

```python
Bend45(BendRadius: float, ID: float, eps: float, **kwargs)
```

Major methods:
- `calc_alpha()`
- `calc_K()`

## Helper Functions in `elements.py`

### `colebrook(...)`

Shared Colebrook residual function used by the pipe and bend friction-factor solver.

### `_solve_friction_factor(...)`

Uses `scipy.optimize.fsolve` to solve the Darcy friction factor from:
- roughness
- diameter
- Reynolds number

## Typical Usage

```python
from fluid_stack import Fluid, Circuit

pressure = 0.10136e6

fluid = Fluid(
    name="JP8.mix",
    temperature=323.15,
    pressure=pressure,
)

circuit = Circuit(
    fluid=fluid,
    mdot=2.0,
    static_pressure=pressure,
)

pump = circuit.pump(
    dP=0.2206e6,
    name="LP_pump",
)

tube = circuit.tube_length(
    length=1.0,
    ID=0.022098,
    eps=0.015e-3,
    name="tube_1",
)

print(tube.pressure_drop)
print(circuit.total_pressure_drop)
print(circuit.static_pressure)
print(circuit.fluid.dynamic_pressure)
print(circuit.fluid.reynolds_number)
```

## How Pressure Is Updated

The current sign convention is:
- resistive elements return positive `pressure_drop`
- pumps return negative `pressure_drop`

The circuit applies:

```python
static_pressure = static_pressure - element.pressure_drop
```

So:
- a positive resistor drop lowers line pressure
- a negative pump drop raises line pressure

`total_pressure_drop` is currently a signed running total, not a losses-only total.

## How Velocity Is Derived

Velocity is not a direct circuit input.

The current model uses:

```python
velocity = mdot / (rho * A)
```

Then:

```python
dynamic_pressure = 0.5 * rho * velocity**2
reynolds_number = rho * velocity * D / mu
```

This means K-based elements require:
- a valid `mdot`
- a usable flow area
- valid REFPROP density and viscosity

## Public Imports

The package exports:

```python
from fluid_stack import (
    Fluid,
    Circuit,
    CircuitElement,
    Pump,
    Orifice,
    TubeLength,
    Bend90,
    Bend45,
)
```

## Current Scope

The current library is a sequential series-circuit framework.

It does support:
- ordered element addition
- REFPROP-backed density and viscosity updates
- pump and resistor chaining
- per-element stored pressure-drop values

It does not yet include:
- branching networks
- automatic solvers for unknown flow rate
- pump curves
- generalized valve classes separate from `Orifice`
- unit-conversion logic
