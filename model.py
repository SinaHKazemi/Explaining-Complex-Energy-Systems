import numpy as np
import pyomo
import pyomo.environ as pyo
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pydantic import BaseModel

class Output(BaseModel):
    objective: float
    variables: dict[str, float|list[float]]

class Settings(BaseModel):
    Lifetime: int
    Price_PV : float
    Price_battery: float
    Cost_buy: float
    Sell_price: float
    Demand_total: float
    
    @property
    def Cost_PV(self):
        return self.Price_PV/self.Lifetime
    
    @property
    def Cost_battery(self):
        return self.Price_battery/self.Lifetime

class HouseModel():
    def __init__(self, settings: Settings, PV_availability: list[float], Demand: list[float]):   
        if len(Demand) != len(PV_availability):
            raise ValueError("Length of the Demand and PV_availability should be equal")
        
        self.settings = settings
        self.Demand = Demand
        # Step 0: Create an instance of the model
        model = pyo.ConcreteModel()
        self.model = model

        # Step 1.1: Define index sets
        T = range(len(Demand)) # hours in one year
        self.T = T

        # dictionary of variables and constraints
        self.variables = {}
        self.constraints = {}
        

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

    # def set_delta_demand(self, values: dict[int,float]) -> None:
    #     """_summary_

    #     :param values: _description_
    #     :type values: dict[int,float]
    #     """
    #     for key,value in values.items():
    #         self.model.delta_demand[key] = value


    def get_output(self) -> dict[str, list[float] | float]:
        output = {}
        print(pyo.value(self.model.primal_obj))
        # objective function
        for obj in self.model.component_objects(pyo.Objective, active=True):
            output["objective"] = pyo.value(obj)
        
        output["variables"] = {}
        for v in self.model.component_objects(pyo.Var, active=True):
            if type(v.index_set()) is not pyomo.core.base.global_set._UnindexedComponent_set:
                output["variables"][str(v)] = []
                for j in v.index_set():
                    output["variables"][str(v)].append(pyo.value(v[j]))
            else:
                output["variables"][str(v)] = pyo.value(v)
        return Output(objective = output["objective"], variables = output["variables"])


    def add_primal(self) -> None:
        settings = self.settings
        PV_availability = self.PV_availability
        Demand = self.Demand
        model = self.model
        T  = self.T
        
        # Step 2: Define the decision variables
        model.energy_PV = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery_in = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_battery_out = pyo.Var(T, within=pyo.NonNegativeReals)
        model.energy_buy = pyo.Var(T, within=pyo.NonNegativeReals)
        model.capacity_PV = pyo.Var(within=pyo.NonNegativeReals)
        model.capacity_battery = pyo.Var(within=pyo.NonNegativeReals)
        model.energy_sell = pyo.Var(T, within=pyo.NonNegativeReals)

        self.variables["primal"] = {
            "energy_PV": model.energy_PV,
            "energy_battery": model.energy_battery,
            "energy_battery_in": model.energy_battery_in,
            "energy_battery_out": model.energy_battery_out,
            "energy_buy": model.energy_buy,
            "capacity_PV": model.capacity_PV,
            "capacity_battery": model.capacity_battery,
            "energy_sell": model.energy_sell,
        }
        
        model.delta_demand = pyo.Var(T, initialize=0, fixed=True)

        # Step 3: Define objective
        model.primal_obj = pyo.Objective(
            expr=settings.Cost_PV * model.capacity_PV
            + settings.Cost_buy * sum(model.energy_buy[i] for i in T)
            + settings.Cost_battery * model.capacity_battery
            - settings.Sell_price * sum(model.energy_sell[i] for i in T),
            sense=pyo.minimize,
        )
        model.primal_obj.deactivate()

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
        
        self.constraints["primal"] = {
            "limit_pv": model.con_limit_pv,
            "limit_battery": model.con_limit_battery,
            "eq_battery": model.con_eq_battery,
            "eq_energy": model.con_eq_energy,
        }

        model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)


    def add_dual(self) -> None:
        if not "primal" in self.variables:
            raise Exception("primal variables and constraints should be added first")
        settings = self.settings
        PV_availability = self.PV_availability
        Demand = self.Demand
        model = self.model
        T  = self.T

        # define dual variables
        model.dual_limit_battery = pyo.Var(T, within=pyo.NonPositiveReals)
        model.dual_limit_PV = pyo.Var(T, within=pyo.NonPositiveReals)
        model.dual_eq_battery = pyo.Var(T, within=pyo.Reals)
        model.dual_eq_demand = pyo.Var(T, within=pyo.Reals)
        
        self.variables["dual"] = {
            "limit_battery": model.dual_limit_battery,
            "limit_PV": model.dual_limit_PV,
            "eq_battery": model.dual_eq_battery,
            "eq_demand": model.dual_eq_demand,
        }

        
        # dual objective
        model.dual_obj = pyo.Objective(expr = sum(model.dual_eq_demand[i] * (Demand[i] + model.delta_demand[i]) * settings.Demand_total for i in T), sense=pyo.maximize)
        model.dual_obj.deactivate()

        # dual feasibility constraints
        model.con_dual_energy_buy = pyo.ConstraintList()
        for i in T:
            model.con_dual_energy_buy.add(model.dual_eq_demand[i] <= settings.Cost_buy)
        
        model.con_dual_energy_sell = pyo.ConstraintList()
        for i in T:
            model.con_dual_energy_sell.add( - model.dual_eq_demand[i] <= - settings.Sell_price)
        
        model.con_dual_energy_battery_out = pyo.ConstraintList()
        for i in T:
            model.con_dual_energy_battery_out.add(model.dual_eq_demand[i] - model.dual_eq_battery[i] <= 0)
        
        model.con_dual_energy_battery_in = pyo.ConstraintList()
        for i in T:
            model.con_dual_energy_battery_in.add(- model.dual_eq_demand[i] + model.dual_eq_battery[i] <= 0)

        model.con_dual_energy_battery = pyo.ConstraintList()
        for i in T:
            model.con_dual_energy_battery.add(model.dual_eq_battery[i] - model.dual_eq_battery[T[i-1]] + model.dual_limit_battery[T[i-1]] <= 0)

        model.con_dual_energy_PV = pyo.ConstraintList()
        for i in T:
            model.con_dual_energy_PV.add( model.dual_eq_demand[i] + model.dual_limit_PV[i] <= 0)

        model.con_dual_capacity_battery = pyo.Constraint(expr = - sum(model.dual_limit_battery[i] for i in T) <= settings.Cost_battery)
        model.con_dual_capacity_PV = pyo.Constraint(expr = - sum(model.dual_limit_PV[i] * PV_availability[i] for i in T) <= settings.Cost_PV)

        self.constraints["dual"] = {
            "energy_buy": model.con_dual_energy_buy,
            "energy_sell": model.con_dual_energy_sell,
            "energy_battery_out": model.con_dual_energy_battery_out,
            "energy_battery_in": model.con_dual_energy_battery_in,
            "energy_battery": model.con_dual_energy_battery,
            "energy_PV": model.con_dual_energy_PV,
            "capacity_battery": model.con_dual_capacity_battery,
            "capacity_PV": model.con_dual_capacity_PV,
        }


    def add_big_M(self, M) -> None:
        if not ("primal" in self.variables or "dual" in self.variables):
            raise Exception("primal and dual variables and constraints should be added first")
        
        settings = self.settings
        PV_availability = self.PV_availability
        model = self.model
        T  = self.T

        # Binary variables
        model.binary_dual_limit_PV = pyo.Var(T, within=pyo.Binary)
        model.binary_dual_limit_battery = pyo.Var(T, within=pyo.Binary)
        model.binary_energy_buy = pyo.Var(T, within=pyo.Binary)
        model.binary_energy_sell = pyo.Var(T, within=pyo.Binary)
        model.binary_energy_battery_out = pyo.Var(T, within=pyo.Binary)
        model.binary_energy_battery_in = pyo.Var(T, within=pyo.Binary)
        model.binary_energy_battery = pyo.Var(T, within=pyo.Binary)
        model.binary_energy_PV = pyo.Var(T, within=pyo.Binary)
        model.binary_capacity_PV = pyo.Var(within=pyo.Binary)
        model.binary_capacity_battery = pyo.Var(within=pyo.Binary)

        self.variables["big-M"] = {
            "dual_limit_PV": model.binary_dual_limit_PV,
            "dual_limit_battery": model.binary_dual_limit_battery,
            "energy_buy": model.binary_energy_buy,
            "energy_sell": model.binary_energy_sell,
            "energy_battery_out": model.binary_energy_battery_out,
            "energy_battery_in": model.binary_energy_battery_in,
            "energy_battery": model.binary_energy_battery,
            "energy_PV": model.binary_energy_PV,
            "capacity_PV": model.binary_capacity_PV,
            "capacity_battery": model.binary_capacity_battery,
        }

        # complementary slackness
        model.con_cs_dual_limit_PV_A = pyo.ConstraintList()
        model.con_cs_dual_limit_PV_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_dual_limit_PV_A.add((- model.dual_limit_PV[i]) <= M*model.binary_dual_limit_PV[i])
            model.con_cs_dual_limit_PV_B.add((model.capacity_PV * PV_availability[i] - model.energy_PV[i]) <= M*(1-model.binary_dual_limit_PV[i]))
        
        model.con_cs_dual_limit_battery_A = pyo.ConstraintList()
        model.con_cs_dual_limit_battery_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_dual_limit_battery_A.add((- model.dual_limit_battery[i]) <= M*model.binary_dual_limit_battery[i])
            model.con_cs_dual_limit_battery_B.add( model.capacity_battery-model.energy_battery[i] <= M*(1-model.binary_dual_limit_battery[i]) )
        
        model.con_cs_energy_buy_A = pyo.ConstraintList()
        model.con_cs_energy_buy_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_energy_buy_A.add(model.energy_buy[i] <= M*model.binary_energy_buy[i])
            model.con_cs_energy_buy_B.add((settings.Cost_buy-model.dual_eq_demand[i]) <= M*(1-model.binary_energy_buy[i]))

        model.con_cs_energy_sell_A = pyo.ConstraintList()
        model.con_cs_energy_sell_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_energy_sell_A.add(model.energy_sell[i] <= M*model.binary_energy_sell[i])
            model.con_cs_energy_sell_B.add((model.dual_eq_demand[i]-settings.Sell_price) <= M*(1-model.binary_energy_sell[i]))

        model.con_cs_energy_battery_out_A = pyo.ConstraintList()
        model.con_cs_energy_battery_out_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_energy_battery_out_A.add(model.energy_battery_out[i] <= M * model.binary_energy_battery_out[i])
            model.con_cs_energy_battery_out_B.add((model.dual_eq_battery[i]-model.dual_eq_demand[i]) <= M * (1 - model.binary_energy_battery_out[i]))
        
        model.con_cs_energy_battery_in_A = pyo.ConstraintList()
        model.con_cs_energy_battery_in_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_energy_battery_in_A.add(model.energy_battery_in[i] <= M*model.binary_energy_battery_in[i])
            model.con_cs_energy_battery_in_B.add((model.dual_eq_demand[i] - model.dual_eq_battery[i]) <= M*(1-model.binary_energy_battery_in[i]))
        
        model.con_cs_energy_battery_A = pyo.ConstraintList()
        model.con_cs_energy_battery_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_energy_battery_A.add(model.energy_battery[T[i-1]] <= M*model.binary_energy_battery[i])
            model.con_cs_energy_battery_B.add((- model.dual_eq_battery[i] + model.dual_eq_battery[T[i-1]] - model.dual_limit_battery[T[i-1]]) <= M*(1-model.binary_energy_battery[i]))
        
        model.con_cs_energy_PV_A = pyo.ConstraintList()
        model.con_cs_energy_PV_B = pyo.ConstraintList()
        for i in T:
            model.con_cs_energy_PV_A.add(model.energy_PV[i] <= M*model.binary_energy_PV[i])
            model.con_cs_energy_PV_B.add((- model.dual_eq_demand[i] - model.dual_limit_PV[i]) <= M*(1-model.binary_energy_PV[i]))
        
        model.con_cs_capacity_battery_A = pyo.Constraint(expr = (model.capacity_battery) <= M*model.binary_capacity_battery)
        model.con_cs_capacity_battery_B = pyo.Constraint(expr = (settings.Cost_battery + sum(model.dual_limit_battery[i] for i in T)) <= M*(1-model.binary_capacity_battery))
        
        model.con_cs_capacity_PV_A = pyo.Constraint(expr = model.capacity_PV <= model.binary_capacity_PV * M)
        model.con_cs_capacity_PV_B = pyo.Constraint(expr = (settings.Cost_PV + sum(model.dual_limit_PV[i] * PV_availability[i] for i in T)) <= (1-model.binary_capacity_PV) * M)

        self.constraints["big-M"] = {
            "dual_limit_PV_A": model.con_cs_dual_limit_PV_A,
            "dual_limit_PV_B": model.con_cs_dual_limit_PV_B,
            "dual_limit_battery_A": model.con_cs_dual_limit_battery_A,
            "dual_limit_battery_B": model.con_cs_dual_limit_battery_B,
            "energy_buy_A" : model.con_cs_energy_buy_A,
            "energy_buy_B" : model.con_cs_energy_buy_B,
            "energy_sell_A": model.con_cs_energy_sell_A,
            "energy_sell_B": model.con_cs_energy_sell_B,
            "energy_battery_out_A": model.con_cs_energy_battery_out_A,
            "energy_battery_out_B": model.con_cs_energy_battery_out_B,
            "energy_battery_in_A": model.con_cs_energy_battery_in_A,
            "energy_battery_in_B": model.con_cs_energy_battery_in_B,
            "energy_battery_A": model.con_cs_energy_battery_A,
            "energy_battery_B": model.con_cs_energy_battery_B,
            "energy_PV_A": model.con_cs_energy_PV_A,
            "energy_PV_B": model.con_cs_energy_PV_B,
            "capacity_battery_A": model.con_cs_capacity_battery_A,
            "capacity_battery_B": model.con_cs_capacity_battery_B,
            "capacity_PV_A": model.con_cs_capacity_PV_A,
            "capacity_PV_B": model.con_cs_capacity_PV_B,
        }
    
    def add_SOS(self)->None:
        settings = self.settings
        PV_availability = self.PV_availability
        model = self.model
        T  = self.T
        
        model.con_sos_dual_limit_PV = pyo.ConstraintList()
        for i in T:
            model.con_sos_dual_limit_PV = pyo.SOSConstraint(model.dual_limit_PV[i],level=1)
            



    def add_upper_level(self, upper_settings: UpperSettings) -> None:
        
        # release delta variable
        model.delta_demand.fixed = False
        
        # define constraints