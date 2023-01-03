import numpy as np
import pyomo
import pyomo.environ as pyo
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pydantic import BaseModel

class Output(BaseModel):
    objective: float
    variables: dict[str, float]

class Settings:
    def __init__(self, Lifetime, Price_PV, Price_battery, Cost_buy, Sell_price, Demand_total):
        self.Lifetime = Lifetime
        self.Price_PV = Price_PV
        self.Price_battery = Price_battery
        self.Cost_buy = Cost_buy
        self.Sell_price = Sell_price
        self.Demand_total = Demand_total
    
    @property
    def Cost_PV(self):
        return self.Price_PV/self.Lifetime
    
    @property
    def Cost_battery(self):
        return self.Price_battery/self.Lifetime

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
        self.settings = settings
        self.Demand = Demand
        # Step 0: Create an instance of the model
        model = pyo.ConcreteModel()
        self.model = model

        # Step 1.1: Define index sets
        T = range(720) # hours in one year
        model.T = T


        # Step 2: Define the decision variables
        # Electricity sector
        model.energy_PV = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery_in = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery_out = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_buy = pyo.Var(T, within=pyo.NonNegativeReals)
        model.capacity_PV = pyo.Var(within=pyo.NonNegativeReals)
        model.capacity_battery = pyo.Var(within=pyo.NonNegativeReals)
        model.energy_sell = pyo.Var(T, within=pyo.NonNegativeReals)

        model.delta_demand = pyo.Param(T, default=0, mutable=True)

        # Step 3: Define objective
        model.primal_obj = pyo.Objective(
            expr=settings.Cost_PV * model.capacity_PV
            + settings.Cost_buy * sum(model.energy_buy[i] for i in T)
            + settings.Cost_battery * model.capacity_battery
            - settings.Sell_price * sum(model.energy_sell[i] for i in T),
            sense=pyo.minimize,
        )
        # model.primal_obj.deactivate()

        # Step 4: Constraints
        model.con_limit_pv = pyo.ConstraintList()
        for i in T:
            model.con_limit_pv.add(model.energy_PV[i] <= model.capacity_PV * PV_availability[i])  # PV Upper Limit

        model.con_limit_battery = pyo.ConstraintList()
        for i in T:
            model.con_limit_battery.add(model.energy_battery[i] <= model.capacity_battery)  # Battery Upper Limit

        
        def rule_con_eq_battery(model,i):
            return model.energy_battery[i] == model.energy_battery[T[i - 1]] - model.energy_battery_out[i] + model.energy_battery_in[i]
        model.con_eq_battery = pyo.Constraint(T, rule = rule_con_eq_battery)

        def rule_con_eq_energy(model, i):
            return settings.Demand_total  * (Demand[i] + model.delta_demand[i]) == model.energy_buy[i] + model.energy_battery_out[i] - model.energy_battery_in[i] + model.energy_PV[i] - model.energy_sell[i]
        model.con_eq_energy = pyo.Constraint(T, rule = rule_con_eq_energy)
        
        
        model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)


        # Write model to mps file
        # model.write(filename=r"model.mps", io_options={"symbolic_solver_labels": True})
    
    def solve(self, solver_name = "cplex"):
        solver = SolverFactory(solver_name)
        solver_output = solver.solve(self.model, tee = True)
        if (solver_output.solver.status == SolverStatus.ok) and (solver_output.solver.termination_condition == TerminationCondition.optimal):
            # Do something when the solution in optimal and feasible
            print("Termination Condition is Optimal")
        elif (solver_output.solver.termination_condition == TerminationCondition.infeasible):
            # Do something when model in infeasible
            print("Termination Condition is Infeasible")
        else:
            # Something else is wrong
            print("Solver Termination Condition: ", solver_output.solver.termination_condition)
            print("Solver Status:" ,  solver_output.solver.status)

    def set_delta_demand(self, values: dict[int,float]) -> None:
        """_summary_

        :param values: _description_
        :type values: dict[int,float]
        """
        for key,value in values.items():
            self.model.delta_demand[key] = value


    def get_output(self) -> dict[str, list[float] | float]:
        output = {}
        # output["dual"] = []
        # for i in self.model.T:
        #     output["dual"].append(self.settings.Demand_total  * (self.Demand[i]) * self.model.dual[self.model.con_eq_energy[i]])
        #     if i < 10:
        #         print(self.model.dual[self.model.con_eq_battery[i]])
        # print("dual real", sum(output["dual"]))

        # for i in self.model.T:
        #     if i <10:
        #         # print(pyo.value(self.model.dual_eq_demand[i]))
        #         print(pyo.value(self.model.dual_eq_battery[i]))
        print(pyo.value(self.model.primal_obj))
        # objective function
        for obj in self.model.component_objects(pyo.Objective, active=True):
            output["objective"] = pyo.value(obj)
        
        output["variable"] = {}
        for v in self.model.component_objects(pyo.Var, active=True):
            if type(v.index_set()) is not pyomo.core.base.global_set._UnindexedComponent_set:
                output["variable"][str(v)] = {}
                for j in v.index_set():
                    output["variable"][str(v)][j] = pyo.value(v[j])
            else:
                output["variable"][str(v)] = pyo.value(v)
        return Output(output["objective"], output["variables"])
