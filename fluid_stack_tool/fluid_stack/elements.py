"""Element classes for the fluid circuit framework."""

from __future__ import annotations

from typing import Any
from scipy.optimize import fsolve
import math
import warnings
from .core import CircuitElement


def _scalar(value: float) -> float:
    """Normalize fsolve's scalar-or-array input to a float."""
    return float(value[0]) if hasattr(value, "__len__") else float(value)


def colebrook(
    friction_factor: float,
    roughness: float,
    diameter: float,
    reynolds_number: float,
) -> float:
    """Colebrook equation written as a root-finding residual."""
    normalized_f = _scalar(friction_factor)
    return -1 / math.sqrt(normalized_f) - 2 * math.log10(
        roughness / (3.7 * diameter)
        + 2.51 / (reynolds_number * math.sqrt(normalized_f))
    )


def _solve_friction_factor(
    roughness: float,
    diameter: float,
    reynolds_number: float,
) -> float:
    """Solve for Darcy friction factor from roughness, diameter, and Re."""
    return float(
        fsolve(
            lambda friction_factor: colebrook(
                friction_factor,
                roughness,
                diameter,
                reynolds_number,
            ),
            x0=.0001,
        )[0]
    )


class Orifice(CircuitElement):
    """Any resistor element that will be modeled as an orifice element parameterized by CdA."""

    element_type = "orifice"

    def __init__(self, *, CdA: float, Apt_Area: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # CdA is provided directly; Cd is derived from the reference flow area.
        self.CdA = CdA
        self.Apt_Area = Apt_Area
        self.Cd = self.CdA / Apt_Area

    def summary(self) -> dict[str, Any]:
        summary = super().summary()
        summary["CdA"] = self.CdA
        summary["Apt_Area"] = self.Apt_Area
        summary["Cd"] = self.Cd
        return summary

    def calc_K(self) -> float:
        # Convert the discharge-coefficient form into an equivalent K loss.
        return 1 / self.Cd**2


class Pump(CircuitElement):
    """Pump element placeholder."""

    element_type = "pump"

    def __init__(self, *, dP: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dP = dP

    def summary(self) -> dict[str, Any]:
        summary = super().summary()
        summary["dP"] = self.dP
        return summary

    def calculate_pressure_drop(self, dynamic_pressure: float | None = None) -> float:
        # Pumps return a negative drop because they raise circuit pressure.
        return -self.dP



class TubeLength(CircuitElement):
    """Straight tube segment parameterized by length."""

    element_type = "tube_length"

    def __init__(
        self,
        *,
        length: float,
        ID: float,
        eps: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.length = length
        self.ID = ID
        self.eps = eps
        # Store cross-sectional area because the circuit uses it to update
        # downstream velocity and dynamic pressure.
        self.Area = math.pi * ID**2 / 4.0
        self.f: float | None = None

    def summary(self) -> dict[str, Any]:
        summary = super().summary()
        summary["length"] = self.length
        summary["ID"] = self.ID
        summary["eps"] = self.eps
        summary["Area"] = self.Area
        summary["f"] = self.f
        return summary
    
    def calc_K(self) -> float:
        # Darcy-Weisbach straight-pipe loss written in K-factor form.
        if self.circuit is None or self.circuit.fluid.reynolds_number is None:
            raise ValueError("Fluid Reynolds number is required to calculate tube losses.")
        self.f = _solve_friction_factor(self.eps, self.ID, self.circuit.fluid.reynolds_number)
        return self.f * self.length / self.ID


class Bend90(CircuitElement):
    """90 degree bend placeholder."""

    element_type = "bend_90"

    def __init__(
        self,
        *,
        BendRadius: float,
        ID: float,
        eps: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.BendRadius = BendRadius
        self.ID = ID
        self.r_D = BendRadius/ID
        self.eps = eps
        # Area is tracked so the circuit can update downstream velocity.
        self.Area = math.pi * ID**2 / 4
        self.f: float | None = None

    def summary(self) -> dict[str, Any]:
        summary = super().summary()
        summary["BendRadius"] = self.BendRadius
        summary["ID"] = self.ID
        summary["eps"] = self.eps
        summary["f"] = self.f
        return summary

    def calc_alpha(self) -> float:
        # Correlation factor for a 90-degree bend based on bend-radius ratio.
        return 0.95 + 4.42 * (1 / self.r_D) ** 1.96

    def calc_K(self) -> float:
        # Convert the bend correlation into an equivalent K loss.
        if self.circuit is None or self.circuit.fluid.reynolds_number is None:
            raise ValueError("Fluid Reynolds number is required to calculate bend losses.")
        self.f = _solve_friction_factor(self.eps, self.ID, self.circuit.fluid.reynolds_number)
        alpha = self.calc_alpha()
        K = 0.0175 * alpha * self.f * 90 * self.r_D
        return K


class Bend45(CircuitElement):
    """45 degree bend placeholder."""

    element_type = "bend_45"

    def __init__(
        self,
        *,
        BendRadius: float,
        ID: float,
        eps: float,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.BendRadius = BendRadius
        self.ID = ID
        self.r_D = BendRadius/ID
        self.eps = eps
        # Area is tracked so the circuit can update downstream velocity.
        self.Area = math.pi * ID**2 / 4
        self.f: float | None = None

    def summary(self) -> dict[str, Any]:
        summary = super().summary()
        summary["BendRadius"] = self.BendRadius
        summary["ID"] = self.ID
        summary["eps"] = self.eps
        summary["f"] = self.f
        return summary

    def calc_alpha(self) -> float:
        # Correlation factor for a 45-degree bend based on bend-radius ratio.
        return 1 + 5.13 * (1 / self.r_D) ** 1.47

    def calc_K(self) -> float:
        # Convert the bend correlation into an equivalent K loss.
        if self.circuit is None or self.circuit.fluid.reynolds_number is None:
            raise ValueError("Fluid Reynolds number is required to calculate bend losses.")
        self.f = _solve_friction_factor(self.eps, self.ID, self.circuit.fluid.reynolds_number)
        alpha = self.calc_alpha()
        K = 0.0175 * alpha * self.f * 45 * self.r_D
        return K

class syphon(CircuitElement):
    """ A T shaped intersection such that fluid is removed from flow being tracked"""

    element_type = "syphon"

    def __init__(
            self,
            *,
            syphon_flowrate:float,
            syphon_area:float,
            **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        pressure = self.circuit.fluid.pressure
        temperature = self.circuit.fluid.temperature
        state = self.circuit.fluid.calculate_state(
            pressure=pressure,
            temperature=temperature
        )
        density = state["density"]
        self.Vs = syphon_flowrate/(density*syphon_area)
        self.V1 = self.circuit.mdot/(density*self.circuit.flow_area)

    def calc_K(self) -> float:
        V_ratio = self.Vs/self.V1 

        if 0<=V_ratio and V_ratio <= 0.22:
            K = 1.55*(0.22-V_ratio)**2-0.03
        elif 0.22<=V_ratio and V_ratio <= 1:
            K = 0.65 *(V_ratio-0.22)**2 - 0.03
        else:
            warnings.warn(
                f"syphon velocity ratio {V_ratio} is outside the supported range [0, 1]; returning K=0",
                RuntimeWarning,
                stacklevel=2,
            )
            K=0
        return K
