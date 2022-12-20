import numpy as np
import pyomo.environ as pyo
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition

# configure the parameters of the original pv house model
Default_Settings = {
    "Lifetime": 10,  # Years
    "Cost_PV": 1000,  # €/kW
    "Cost_Battery": 300,  # €/kWh
    "Cost_buy": 0.25,  # €/kWh
    "Sell_price": 0.05,  # €/kWh
    "Demand_total": 3500,  # kWh/Year
}


# create HouseModel
class HouseModel():
    def __init__(self, settings: dict[str, int|float], PV_availability: list[float], Demand: list[float]):
        """_summary_

        :param settings: _description_
        :type settings: dict[str, int | float]
        :param PV_availability: _description_
        :type PV_availability: list[float]
        :param Demand: _description_
        :type Demand: list[float]
        """        
        
        # Step 0: Create an instance of the model
        self.settings = settings
        model = pyo.ConcreteModel()
        self.model = model

        # Step 1.1: Define index sets
        T = range(8760) # hours in one year
        model.T = T

        # Step 1.2: Parameters
        Lifetime = settings["lifetime"]  # lifetime in years
        Cost_PV = settings["cost_PV"] / Lifetime  # € / (lifetime * kW)
        Cost_battery = settings["Cost_Battery"] / Lifetime  # € / (lifetime * kWh)
        Cost_buy = settings["Cost_buy"]  # € / kWh
        Demand_total = settings["Demand_total"]  # kWh
        Sell_price = settings["Sell_price"]  # € / kWh

        # Step 2: Define the decision variables
        # Electricity sector
        model.energy_PV = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery_IN = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery_OUT = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_buy = pyo.Var(T, within=pyo.NonNegativeReals)
        model.capacity_PV = pyo.Var(within=pyo.NonNegativeReals)
        model.capacity_battery = pyo.Var(within=pyo.NonNegativeReals)
        model.sell_energy = pyo.Var(T, within=pyo.NonNegativeReals)

        model.delta_demand = pyo.Param(T, default=0, mutable=True)

        # Step 3: Define objective
        model.cost = pyo.Objective(
            expr=Cost_PV * model.capacity_PV
            + Cost_buy * sum(model.energy_buy[i] for i in T)
            + Cost_battery * model.capacity_battery
            - Sell_price * sum(model.sell_energy[i] for i in T),
            sense=pyo.minimize,
        )

        # Step 4: Constraints
        model.con_limit_pv = pyo.ConstraintList()
        for i in T:
            model.con_limit_pv.add(model.energy_PV[i] <= model.capacity_PV * PV_availability[i])  # PV Upper Limit

        model.con_limit_battery = pyo.ConstraintList()
        for i in T:
            model.con_limit_battery.add(model.energy_battery[i] <= model.capacity_battery)  # Battery Upper Limit

        model.con_eq_battery = pyo.ConstraintList()
        for i in T:
            model.con_eq_battery.add(
                expr=model.energy_battery[i]
                == model.energy_battery[T[i - 1]] - model.energy_battery_out[i] + model.energy_battery_in[i]
            )  # Battery Equation

        model.con_eq_energy = pyo.ConstraintList()
        for i in T:
            model.con_eq_energy.add(
                expr=Demand_total  * (Demand[i] + model.delta_demand[i])
                == model.energy_buy[i]
                + model.energy_battery_out[i]
                - model.energy_battery_in[i]
                + model.energy_PV[i]
                - model.sell_energy[i]
            )  # Energy Equation

        # Write model to mps file
        # model.write(filename=r"model.mps", io_options={"symbolic_solver_labels": True})
    def solve(self, solver_name = "cplex"):
        solver = SolverFactory(solver_name)
        solver_output = solver.solve(self.model)
        if (solver_output.solver.status == SolverStatus.ok) and (solver_output.solver.termination_condition == TerminationCondition.optimal):
            # Do something when the solution in optimal and feasible
            print("Termination Condition is Optimal")
        elif (solver_output.solver.termination_condition == TerminationCondition.infeasible):
            # Do something when model in infeasible
            print("Termination Condition is Infeasible")
        else:
            # Something else is wrong
            print("Solver Status:" ,  solver_output.solver.status)

    def set_delta_demand(self, values: dict[int,float]) -> None:
        """_summary_

        :param values: _description_
        :type values: dict[int,float]
        """
        for key,value in values.items():
            self.model.delta_demand[key] = value


    def get_output(self) -> dict[str, list[float]]:
        return None
