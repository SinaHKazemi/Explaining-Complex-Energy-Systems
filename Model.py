import numpy as np
import pyomo.environ as pyo
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition


# configure the parameters of the original pv house model
def getSettings():
    settingsDict = {
        "Lifetime": 10,  # Years
        "Cost_PV": 1000,  # €/kW
        "Cost_Battery": 300,  # €/kWh
        "Cost_buy": 0.25,  # €/kWh
        "Sell_price": 0.05,  # €/kWh
        "Demand_total": 3500,  # kWh/Year
    }
    return settingsDict


# create HouseModel
class HouseModel():
    def __init__(self, settings: dict[str, int|float], PV_availability: list[float], Demand: list[float]):
        # Step 0: Create an instance of the model
        model = pyo.ConcreteModel()
        self.model = model

        # Step 1.1: Define index sets
        time = range(8760) # hours in one year

        # Step 1.2: Parameters
        Lifetime = settings["lifetime"]  # lifetime in years
        Cost_PV = settings["cost_PV"] / Lifetime  # € / (lifetime * kW)
        Cost_battery = settings["Cost_Battery"] / Lifetime  # € / (lifetime * kWh)
        Cost_buy = settings["Cost_buy"]  # € / kWh
        Demand_total = settings["Demand_total"]  # kWh
        Sell_price = settings["Sell_price"]  # € / kWh

        # Step 2: Define the decision variables
        # Electricity sector
        model.energy_PV = pyo.Var(time, within=pyo.NonNegativeReals)
        model.energy_battery = pyo.Var(time, within=pyo.NonNegativeReals)
        model.energy_battery_IN = pyo.Var(time, within=pyo.NonNegativeReals)
        model.energy_battery_OUT = pyo.Var(time, within=pyo.NonNegativeReals)
        model.energy_buy = pyo.Var(time, within=pyo.NonNegativeReals)
        model.capacity_PV = pyo.Var(within=pyo.NonNegativeReals)
        model.capacity_battery = pyo.Var(within=pyo.NonNegativeReals)
        model.sell_energy = pyo.Var(time, within=pyo.NonNegativeReals)

        # Step 3: Define objective
        model.cost = pyo.Objective(
            expr=Cost_PV * model.capacity_PV
            + Cost_buy * sum(model.energy_buy[i] for i in time)
            + Cost_battery * model.capacity_battery
            - Sell_price * sum(model.sell_energy[i] for i in time),
            sense=pyo.minimize,
        )

        # Step 4: Constraints
        model.limEQpv = pyo.ConstraintList()
        for i in time:
            model.lim_eq_PV.add(model.energy_PV[i] <= model.capacity_PV * PV_availability[i])  # PV Upper Limit

        model.limEQbat = pyo.ConstraintList()
        for i in time:
            model.limEQbat.add(model.energy_battery[i] <= model.capacity_battery)  # Battery Upper Limit

        model.batteryEQ = pyo.ConstraintList()
        for i in time:
            model.batteryEQ.add(
                expr=model.energy_battery[i]
                == model.energy_battery[time[i - 1]] - model.energy_battery_out[i] + model.energy_battery_in[i]
            )  # Battery Equation

        model.EnergyEQ = pyo.ConstraintList()
        for i in time:
            model.EnergyEQ.add(
                expr=Demand_total  * Demand[i]
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

    def get_output(self):
        return None


# run model
def run():
    # start = time.time()
    settings = getSettings()
    PV_availability = np.loadtxt("../time_series/original_pv_availability.csv")
    Demand = np.loadtxt("../time_series/bdew_demand.csv")
    solution = HouseModel(settings, PV_availability, Demand)
    # end = time.time()

    # print output
    print("Capacity for the PV module: " + str(pyo.value(solution.CapacityPV)) + " kW")
    print("Capacity for the battery module: " + str(pyo.value(solution.CapacityBattery)) + " kWh")

    cost_PV_year = settings["cost_PV"] / settings["lifetime"]
    cost_BAT_year = settings["cost_Battery"] / settings["lifetime"]
    print("\nCost of PV module per year: " + str(cost_PV_year) + " €")
    print("Cost of battery module per year: " + str(cost_BAT_year) + " €")
    print(
        "CapEx per year: "
        + str(cost_PV_year * pyo.value(solution.CapacityPV) + cost_BAT_year * pyo.value(solution.CapacityBattery))
        + " €"
    )

    # print("\nExecution of the model took " + str(round(end - start, 2)) + " seconds")


run()