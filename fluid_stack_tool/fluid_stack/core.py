"""Core types for the fluid circuit framework."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from typing import Any

from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary


# Create one module-level REFPROP handle and reuse it everywhere.
# This matches the pattern from the official wrapper examples and keeps
# fluid state calls simple inside the Fluid methods below.
REFPROP = REFPROPFunctionLibrary(os.environ["RPPREFIX"])
REFPROP.SETPATHdll(os.environ["RPPREFIX"])


@dataclass(slots=True)
class ElementResult:
    """Stored result for an element after it is added to a circuit."""

    element: "CircuitElement"
    pressure_drop: float


class Fluid:
    """REFPROP-backed fluid state container."""

    def __init__(
        self,
        name: str,
        *,
        temperature: float,
        pressure: float | None = None,
        composition: list[float] | None = None,
        **properties: Any,
    ) -> None:
        self.name = name
        self.temperature = float(temperature)
        self.pressure = float(pressure) if pressure is not None else None
        self.composition = list(composition) if composition is not None else [1.0]
        self.properties = dict(properties)
        # Everything in this project uses SI units, so resolve the REFPROP
        # enum once and always use the SI mass basis for state calls.
        self._si_mass_basis = REFPROP.GETENUMdll(0, "MASS BASE SI").iEnum
        self.state: dict[str, float] = {}
        # Reynolds number is part of the active fluid state seen by each
        # element as the circuit advances from one component to the next.
        self.reynolds_number: float | None = None
        # Dynamic pressure is also part of the active fluid state used by
        # K-based loss elements.
        self.dynamic_pressure: float | None = None

        # If the user supplied an initial pressure, resolve the starting
        # thermodynamic state immediately so density/viscosity are available.
        if self.pressure is not None:
            self.update_state(pressure=self.pressure)

    def summary(self) -> dict[str, Any]:
        """Return a serializable view of the fluid state."""
        return {
            "name": self.name,
            "temperature": self.temperature,
            "pressure": self.pressure,
            "composition": list(self.composition),
            "reynolds_number": self.reynolds_number,
            "dynamic_pressure": self.dynamic_pressure,
            "state": dict(self.state),
            "properties": dict(self.properties),
        }

    def calculate_state(
        self,
        *,
        pressure: float | None = None,
        temperature: float | None = None,
    ) -> dict[str, float]:
        """Calculate the fluid state with REFPROP."""
        # Use explicit function inputs when they are provided; otherwise fall
        # back to the Fluid object's currently stored pressure/temperature.
        resolved_pressure = self.pressure if pressure is None else float(pressure)
        resolved_temperature = self.temperature if temperature is None else float(temperature)

        if resolved_pressure is None:
            raise ValueError("Pressure is required for REFPROP state calculations.")

        # Query REFPROP directly with a T,P state and ask for density/viscosity.
        # Try the current composition first; if REFPROP rejects it for a
        # predefined mixture, retry with a zero composition vector.
        try:
            result = REFPROP.REFPROPdll(
                self.name,
                "TP",
                "D;VIS",
                self._si_mass_basis,
                0,
                0,
                resolved_temperature,
                resolved_pressure,
                self.composition,
            )
            if result.ierr > 0:
                raise ValueError(result.herr.strip())
        except ValueError:
            fallback_composition = [0.0]
            result = REFPROP.REFPROPdll(
                self.name,
                "TP",
                "D;VIS",
                self._si_mass_basis,
                0,
                0,
                resolved_temperature,
                resolved_pressure,
                fallback_composition,
            )
            if result.ierr <= 0:
                self.composition = fallback_composition

        # REFPROP uses negative ierr values for warnings and positive values
        # for actual errors. Allow warnings to pass through so mixture files
        # like JP8.mix behave the same way they do in the GUI.
        if result.ierr > 0:
            raise ValueError(
                f"REFPROP failed for {self.name} at T={resolved_temperature}, P={resolved_pressure}: "
                f"{result.herr.strip()}"
            )

        return {
            "temperature": resolved_temperature,
            "pressure": resolved_pressure,
            "density": float(result.Output[0]),
            "viscosity": float(result.Output[1]),
        }

    def update_state(
        self,
        *,
        pressure: float | None = None,
        temperature: float | None = None,
    ) -> dict[str, float]:
        """Calculate and store the latest REFPROP state."""
        # Store the resolved state on the object so the circuit can reuse the
        # latest density/viscosity without tracking separate copies itself.
        state = self.calculate_state(pressure=pressure, temperature=temperature)
        self.temperature = state["temperature"]
        self.pressure = state["pressure"]
        self.state = state
        self.properties["density"] = state["density"]
        self.properties["viscosity"] = state["viscosity"]
        return state

    def calculate_density(self, pressure: float | None = None) -> float:
        """Return the fluid density at the requested state."""
        return self.update_state(pressure=pressure)["density"]

    def calculate_viscosity(self, pressure: float | None = None) -> float:
        """Return the fluid viscosity at the requested state."""
        return self.update_state(pressure=pressure)["viscosity"]

    def update_reynolds_number(
        self,
        *,
        density: float,
        velocity: float,
        diameter: float,
        viscosity: float,
    ) -> float:
        """Calculate and store Reynolds number for the current flow state."""
        self.reynolds_number = density * velocity * diameter / viscosity
        return self.reynolds_number

    def update_dynamic_pressure(
        self,
        *,
        density: float,
        velocity: float,
    ) -> float:
        """Calculate and store dynamic pressure for the current flow state."""
        self.dynamic_pressure = 0.5 * density * velocity**2
        return self.dynamic_pressure

    def __repr__(self) -> str:
        return (
            f"Fluid(name={self.name!r}, temperature={self.temperature!r}, "
            f"pressure={self.pressure!r}, properties={self.properties!r})"
        )


class CircuitElement:
    """Base class for all pumps and resistors in a circuit."""

    element_type = "circuit_element"

    def __init__(
        self,
        *,
        name: str | None = None,
        element_id: str | None = None,
        **parameters: Any,
    ) -> None:
        existing_circuit = getattr(self, "circuit", None)
        self.name = name
        self.element_id = element_id
        self.parameters = dict(parameters)
        self.circuit: Circuit | None = existing_circuit
        self.pressure_drop: float | None = None

    def calculate_pressure_drop(self, dynamic_pressure: float | None = None) -> float:
        """Return the pressure drop for this element."""
        if dynamic_pressure is None and self.circuit is not None:
            dynamic_pressure = self.circuit.fluid.dynamic_pressure

        if dynamic_pressure is None:
            raise ValueError(
                f"{self.__class__.__name__} requires fluid dynamic pressure to calculate dP. "
                "Provide circuit mdot and an element area so q = 0.5 * rho * v^2 can be calculated."
            )

        # The default element model is "K-based": element subclasses provide
        # calc_K(), and the shared pressure-drop path converts that into dP.
        calc_k = getattr(self, "calc_K", None)
        if callable(calc_k):
            return dynamic_pressure * float(calc_k())

        raise NotImplementedError(
            f"{self.__class__.__name__} must define calc_K() or override calculate_pressure_drop()."
        )

    def update_pressure_drop(self, dynamic_pressure: float | None = None) -> float:
        """Recalculate and store the pressure drop for this element."""
        pressure_drop = self.calculate_pressure_drop(dynamic_pressure)
        self.pressure_drop = pressure_drop
        return pressure_drop

    def summary(self) -> dict[str, Any]:
        """Return a serializable view of this element."""
        return {
            "type": self.element_type,
            "name": self.name,
            "element_id": self.element_id,
            "pressure_drop": self.pressure_drop,
            "parameters": dict(self.parameters),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"element_id={self.element_id!r}, "
            f"pressure_drop={self.pressure_drop!r}, "
            f"parameters={self.parameters!r})"
        )


class Circuit:
    """Ordered container for a fluid and the elements attached to it."""

    def __init__(
        self,
        *,
        fluid: Fluid,
        mdot: float | None = None,
        static_pressure: float | None = None,
        flow_area: float | None = None,
    ) -> None:
        if not isinstance(fluid, Fluid):
            raise TypeError("Circuit requires a Fluid instance.")

        self.fluid = fluid
        # static_pressure is the running line pressure used for REFPROP state
        # updates after each element is added.
        self.static_pressure = (
            float(static_pressure)
            if static_pressure is not None
            else self.fluid.pressure
        )
        # Resolve the initial density from the current fluid state before any
        # circuit elements are added.
        self.density = 0.0
        self.viscosity: float | None = None
        self._refresh_fluid_state(self.static_pressure)
        # Velocity is always derived from mass flow rate and area; it is not
        # provided directly by the caller.
        self.velocity: float | None = None
        self.fluid.dynamic_pressure = None
        self.flow_area = float(flow_area) if flow_area is not None else None
        self.mdot = float(mdot) if mdot is not None else None
        self.elements: list[CircuitElement] = []
        self.total_pressure_drop = 0.0
        self.pressure_drop_history: list[ElementResult] = []
        self._initialize_hydraulic_state()

    def _initialize_hydraulic_state(self) -> None:
        """Initialize derived hydraulic state when area is already known."""
        self._update_flow_kinematics(self.flow_area)

    def _element_flow_area(self, element: CircuitElement) -> float | None:
        """Return the representative flow area for an element when available."""
        # Prefer an explicitly stored area, otherwise infer it from diameter.
        if hasattr(element, "Apt_Area"):
            return float(getattr(element, "Apt_Area"))
        if hasattr(element, "Area"):
            return float(getattr(element, "Area"))
        if hasattr(element, "ID"):
            diameter = float(getattr(element, "ID"))
            return math.pi * diameter**2 / 4.0
        return None

    def _refresh_fluid_state(self, pressure: float | None) -> None:
        """Update density and viscosity together from REFPROP."""
        state = self.fluid.update_state(pressure=pressure)
        self.density = state["density"]
        self.viscosity = state["viscosity"]

    def _update_flow_kinematics(self, flow_area: float | None) -> None:
        """Derive velocity and dynamic pressure from mdot and area."""
        if flow_area is not None:
            self.flow_area = flow_area

        if self.mdot is None or self.flow_area is None:
            self.velocity = None
            self.fluid.dynamic_pressure = None
            return

        self.velocity = self.mdot / (self.density * self.flow_area)
        self.fluid.update_dynamic_pressure(
            density=self.density,
            velocity=self.velocity,
        )

    def _update_fluid_reynolds_number(self, element: CircuitElement) -> None:
        """Update fluid Reynolds number before a non-pump element is evaluated."""
        if element.element_type == "pump":
            return
        if self.velocity is None or self.viscosity is None or not hasattr(element, "ID"):
            self.fluid.reynolds_number = None
            return

        self.fluid.update_reynolds_number(
            density=self.density,
            velocity=self.velocity,
            diameter=float(getattr(element, "ID")),
            viscosity=self.viscosity,
        )

    def _recalculate_hydraulic_state(self, element: CircuitElement) -> None:
        """Update density, velocity, and dynamic pressure after an element is added."""
        if element.pressure_drop is None:
            return

        # Each element now owns its own pressure sign convention. A loss element
        # returns a positive pressure_drop, while a pressure source returns a
        # negative one. The circuit only applies the returned value.
        if self.static_pressure is not None:
            self.static_pressure -= element.pressure_drop

        previous_density = self.density

        # Refresh fluid properties from REFPROP at the new static pressure.
        self._refresh_fluid_state(self.static_pressure)

        element_area = self._element_flow_area(element)
        self._update_flow_kinematics(element_area if element_area is not None else self.flow_area)

    def _add_element(self, element: CircuitElement) -> CircuitElement:
        """Attach an element to the circuit and compute its pressure drop."""
        if not isinstance(element, CircuitElement):
            raise TypeError("Circuit can only add CircuitElement instances.")

        element.circuit = self

        try:
            self._update_flow_kinematics(self._element_flow_area(element))
            self._update_fluid_reynolds_number(element)
            # First compute the element dP from the current hydraulic state.
            pressure_drop = element.update_pressure_drop()
        except Exception:
            element.circuit = None
            element.pressure_drop = None
            raise

        self.elements.append(element)
        self.total_pressure_drop += pressure_drop
        self.pressure_drop_history.append(
            ElementResult(element=element, pressure_drop=pressure_drop)
        )
        # Then update the line state so the next element sees the new density,
        # velocity, and dynamic pressure.
        self._recalculate_hydraulic_state(element)
        return element

    def orifice(self, CdA: float, Apt_Area: float, **kwargs: Any):
        """Add an orifice-like loss element to the circuit."""
        from .elements import Orifice

        return self._add_element(Orifice(CdA=CdA, Apt_Area=Apt_Area, **kwargs))

    def pump(self, *, dP: float, **kwargs: Any):
        """Add a pump element that contributes a direct pressure rise."""
        from .elements import Pump

        return self._add_element(Pump(dP=dP, **kwargs))

    def tube_length(
        self,
        *,
        length: float,
        ID: float,
        eps: float,
        **kwargs: Any,
    ):
        """Add a straight pipe section."""
        from .elements import TubeLength

        return self._add_element(
            TubeLength(
                length=length,
                ID=ID,
                eps=eps,
                **kwargs,
            )
        )

    def bend_90(
        self,
        *,
        BendRadius: float,
        ID: float,
        eps: float,
        **kwargs: Any,
    ):
        """Add a 90-degree bend."""
        from .elements import Bend90

        return self._add_element(
            Bend90(
                BendRadius=BendRadius,
                ID=ID,
                eps=eps,
                **kwargs,
            )
        )

    def bend_45(
        self,
        *,
        BendRadius: float,
        ID: float,
        eps: float,
        **kwargs: Any,
    ):
        """Add a 45-degree bend."""
        from .elements import Bend45

        return self._add_element(
            Bend45(
                BendRadius=BendRadius,
                ID=ID,
                eps=eps,
                **kwargs,
            )
        )

    def syphon(
        self,
        *,
        syphon_flowrate: float,
        syphon_area: float,
        **kwargs: Any,
    ):
        """Add a siphon branch that removes flow from the tracked circuit."""
        from .elements import syphon

        if self.mdot is None:
            raise ValueError("Circuit mdot is required to add a syphon.")
        if self.flow_area is None:
            raise ValueError("Circuit flow_area is required to add a syphon.")
        if syphon_area <= 0:
            raise ValueError("syphon_area must be greater than zero.")
        if syphon_flowrate < 0:
            raise ValueError("syphon_flowrate cannot be negative.")
        if syphon_flowrate > self.mdot:
            raise ValueError("syphon_flowrate cannot exceed circuit mdot.")

        element = syphon.__new__(syphon)
        element.circuit = self
        syphon.__init__(
            element,
            syphon_flowrate=syphon_flowrate,
            syphon_area=syphon_area,
            **kwargs,
        )
        element = self._add_element(element)
        self.mdot -= syphon_flowrate
        self._update_flow_kinematics(self.flow_area)
        return element

    def summary(self) -> dict[str, Any]:
        """Return a serializable summary of the circuit."""
        return {
            "fluid": self.fluid.summary(),
            "density": self.density,
            "viscosity": self.fluid.state.get("viscosity"),
            "mdot": self.mdot,
            "velocity": self.velocity,
            "dynamic_pressure": self.fluid.dynamic_pressure,
            "static_pressure": self.static_pressure,
            "flow_area": self.flow_area,
            "total_pressure_drop": self.total_pressure_drop,
            "elements": [element.summary() for element in self.elements],
        }

    def __repr__(self) -> str:
        return (
            f"Circuit(fluid={self.fluid!r}, "
            f"element_count={len(self.elements)}, "
            f"total_pressure_drop={self.total_pressure_drop!r})"
        )
