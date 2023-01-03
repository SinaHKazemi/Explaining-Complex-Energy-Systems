from model import HouseModel, Settings
import pyomo.environ as pyo
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import pyomo

class BaseKKT(HouseModel):
    def __init__(self, settings: Settings, PV_availability: list[float], Demand: list[float]):
        super().__init__(settings, PV_availability, Demand)
        model = self.model

        # define dual variables
        model.dual_limit_battery = pyo.Var(model.T, within=pyo.NonPositiveReals)
        model.dual_limit_PV = pyo.Var(model.T, within=pyo.NonPositiveReals)
        model.dual_eq_battery = pyo.Var(model.T, within=pyo.Reals)
        model.dual_eq_demand = pyo.Var(model.T, within=pyo.Reals)
        model.dual_obj = pyo.Var(within = pyo.Reals)

        # dual feasibility constraints

        model.dual_obj = pyo.Objective(expr = sum(model.dual_eq_demand[i] * Demand[i] * settings.Demand_total for i in model.T), sense=pyo.maximize)
        model.dual_obj.deactivate()

        model.con_dual_energy_buy = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_buy.add(model.dual_eq_demand[i] <= settings.Cost_buy)
        
        model.con_dual_energy_sell = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_sell.add( - model.dual_eq_demand[i] <= - settings.Sell_price)
        
        model.con_dual_energy_battery_out = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_battery_out.add(model.dual_eq_demand[i] - model.dual_eq_battery[i] <= 0)
        
        model.con_dual_energy_battery_in = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_battery_in.add(- model.dual_eq_demand[i] + model.dual_eq_battery[i] <= 0)

        model.con_dual_energy_battery = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_battery.add(model.dual_eq_battery[i] - model.dual_eq_battery[model.T[i-1]] + model.dual_limit_battery[model.T[i-1]] <= 0)

        model.con_dual_energy_PV = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_PV.add( model.dual_eq_demand[i] + model.dual_limit_PV[i] <= 0)

        model.con_dual_capacity_battery = pyo.Constraint(expr = - sum(model.dual_limit_battery[i] for i in model.T) <= settings.Cost_battery)
        model.con_dual_capacity_PV = pyo.Constraint(expr = - sum(model.dual_limit_PV[i] * PV_availability[i] for i in model.T) <= settings.Cost_PV)
    
class NonlinearKKT(BaseKKT):
    def __init__(self, settings: Settings, PV_availability: list[float], Demand: list[float]):
        super().__init__(settings, PV_availability, Demand)
        model = self.model

        # complementary slackness
        model.con_cs_dual_limit_PV = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_PV.add((- model.dual_limit_PV[i])*(model.capacity_PV * PV_availability[i] -model.energy_PV[i]) == 0)
        
        model.con_cs_dual_limit_battery = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_battery.add((- model.dual_limit_battery[i])*(model.capacity_battery-model.energy_battery[i]) == 0)
        
        model.con_cs_energy_buy = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_buy.add(model.energy_buy[i]*(settings.Cost_buy-model.dual_eq_demand[i]) == 0)

        model.con_cs_energy_sell = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_sell.add(model.energy_sell[i]*(model.dual_eq_demand[i]-settings.Sell_price) == 0)
        
        model.con_cs_energy_battery_out = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_out.add(model.energy_battery_out[i]*(model.dual_eq_battery[i]-model.dual_eq_demand[i]) == 0)
        
        model.con_cs_energy_battery_in = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_in.add(model.energy_battery_in[i]*(model.dual_eq_demand[i] - model.dual_eq_battery[i]) == 0)
        
        model.con_cs_energy_battery = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery.add(model.energy_battery[model.T[i-1]]*(- model.dual_eq_battery[i] + model.dual_eq_battery[model.T[i-1]] - model.dual_limit_battery[model.T[i-1]]) == 0)
        
        model.con_cs_energy_PV = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_PV.add(model.energy_PV[i]*(- model.dual_eq_demand[i] - model.dual_limit_PV[i]) == 0)
        
        model.con_cs_capacity_battery = pyo.Constraint(expr = (settings.Cost_battery + sum(model.dual_limit_battery[i] for i in model.T))(model.capacity_battery) == 0)
        model.con_cs_capacity_PV = pyo.Constraint(expr = (settings.Cost_PV + sum(model.dual_limit_PV[i] * PV_availability[i] for i in model.T))(model.capacity_PV) == 0)

class FortunyKKT(BaseKKT):
    def __init__(self, settings: Settings, PV_availability: list[float], Demand: list[float]):
        super().__init__(settings, PV_availability, Demand)
        model = self.model

        M = 100 # it should be changed

        # Binary variables
        model.binary_dual_limit_PV = pyo.Var(model.T, within=pyo.Binary)
        model.binary_dual_limit_battery = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_buy = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_sell = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_battery_out = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_battery_in = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_battery = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_PV = pyo.Var(model.T, within=pyo.Binary)
        model.binary_capacity_PV = pyo.Var(within=pyo.Binary)
        model.binary_capacity_battery = pyo.Var(within=pyo.Binary)

        # complementary slackness
        model.con_cs_dual_limit_PV_A = pyo.ConstraintList()
        model.con_cs_dual_limit_PV_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_PV_A.add((- model.dual_limit_PV[i]) <= M*model.binary_dual_limit_PV[i])
            model.con_cs_dual_limit_PV_B.add((model.capacity_PV * PV_availability[i] - model.energy_PV[i]) <= M*(1-model.binary_dual_limit_PV[i]))
        
        model.con_cs_dual_limit_battery_A = pyo.ConstraintList()
        model.con_cs_dual_limit_battery_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_battery_A.add((- model.dual_limit_battery[i]) <= M*model.binary_dual_limit_battery[i])
            model.con_cs_dual_limit_battery_B.add( model.capacity_battery-model.energy_battery[i] <= M*(1-model.binary_dual_limit_battery[i]) )
        
        model.con_cs_energy_buy_A = pyo.ConstraintList()
        model.con_cs_energy_buy_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_buy_A.add(model.energy_buy[i] <= M*model.binary_energy_buy[i])
            model.con_cs_energy_buy_B.add((settings.Cost_buy-model.dual_eq_demand[i]) <= M*(1-model.binary_energy_buy[i]))

        model.con_cs_energy_sell_A = pyo.ConstraintList()
        model.con_cs_energy_sell_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_sell_A.add(model.energy_sell[i] <= M*model.binary_energy_sell[i])
            model.con_cs_energy_sell_B.add((model.dual_eq_demand[i]-settings.Sell_price) <= M*(1-model.binary_energy_sell[i]))

        model.con_cs_energy_battery_out_A = pyo.ConstraintList()
        model.con_cs_energy_battery_out_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_out_A.add(model.energy_battery_out[i] <= M * model.binary_energy_battery_out[i])
            model.con_cs_energy_battery_out_B.add((model.dual_eq_battery[i]-model.dual_eq_demand[i]) <= M * (1 - model.binary_energy_battery_out[i]))
        
        model.con_cs_energy_battery_in_A = pyo.ConstraintList()
        model.con_cs_energy_battery_in_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_in_A.add(model.energy_battery_in[i] <= M*model.binary_energy_battery_in[i])
            model.con_cs_energy_battery_in_B.add((model.dual_eq_demand[i] - model.dual_eq_battery[i]) <= M*(1-model.binary_energy_battery_in[i]))
        
        model.con_cs_energy_battery_A = pyo.ConstraintList()
        model.con_cs_energy_battery_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_A.add(model.energy_battery[model.T[i-1]] <= M*model.binary_energy_battery[i])
            model.con_cs_energy_battery_B.add((- model.dual_eq_battery[i] + model.dual_eq_battery[model.T[i-1]] - model.dual_limit_battery[model.T[i-1]]) <= M*(1-model.binary_energy_battery[i]))
        
        model.con_cs_energy_PV_A = pyo.ConstraintList()
        model.con_cs_energy_PV_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_PV_A.add(model.energy_PV[i] <= M*model.binary_energy_PV[i])
            model.con_cs_energy_PV_B.add((- model.dual_eq_demand[i] - model.dual_limit_PV[i]) <= M*(1-model.binary_energy_PV[i]))
        
        model.con_cs_capacity_battery_A = pyo.Constraint(expr = (model.capacity_battery) <= M*model.binary_capacity_battery)
        model.con_cs_capacity_battery_B = pyo.Constraint(expr = (settings.Cost_battery + sum(model.dual_limit_battery[i] for i in model.T)) <= M*(1-model.binary_capacity_battery))
        
        model.con_cs_capacity_PV_A = pyo.Constraint(expr = model.capacity_PV <= model.binary_capacity_PV * M)
        model.con_cs_capacity_PV_B = pyo.Constraint(expr = (settings.Cost_PV + sum(model.dual_limit_PV[i] * PV_availability[i] for i in model.T)) <= (1-model.binary_capacity_PV) * M)