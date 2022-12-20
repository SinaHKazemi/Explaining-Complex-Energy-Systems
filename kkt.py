from model import HouseModel
import pyomo.environ as pyo

class BaseKKT(HouseModel):
    def __init__(self, settings: dict[str, int | float], PV_availability: list[float], Demand: list[float]):
        super().__init__(settings, PV_availability, Demand)
        model = self.model
        # define dual variables
        model.dual_limit_battery = pyo.Var(model.T, within=pyo.NonPositiveReals)
        model.dual_limit_PV = pyo.Var(model.T, within=pyo.NonPositiveReals)
        model.dual_eq_battery = pyo.Var(model.T, within=pyo.Reals)
        model.dual_eq_demand = pyo.Var(model.T, within=pyo.Reals)

        # dual feasibility constraints
        Cost_buy = self.settings["Cost_buy"]
        Cost_sell = self.settings["Cost_sell"]

        model.con_dual_energy_buy = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_buy.add(model.dual_eq_demand[i] <= Cost_buy)
        
        model.con_dual_energy_sell = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_sell.add(model.dual_eq_demand[i] >= Cost_sell)
        
        model.con_dual_energy_battery_out = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_battery_out.add(model.dual_eq_demand[i] - model.dual_eq_battery[i] <= 0)
        
        model.con_dual_energy_battery_in = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_battery_in.add(- model.dual_eq_demand[i] + model.dual_eq_battery[i] <= 0)

        model.con_dual_energy_battery = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_battery.add(- model.dual_eq_battery[i] + model.dual_limit_battery[i] <= 0)

        model.con_dual_energy_PV = pyo.ConstraintList()
        for i in model.T:
            model.con_dual_energy_PV.add( model.dual_eq_demand[i] + model.dual_limit_PV[i] <= 0)


class NonlinearKKT(BaseKKT):
    def __init__(self, settings: dict[str, int | float], PV_availability: list[float], Demand: list[float]):
        super().__init__(settings, PV_availability, Demand)
        model = self.model
        Cost_buy = self.settings["Cost_buy"]
        Cost_sell = self.settings["Cost_sell"]

        # complementary slackness
        model.con_cs_dual_limit_PV = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_PV.add((- model.dual_limit_PV[i])*(model.capacity_PV[i]-model.energy_PV[i]) == 0)
        
        model.con_cs_dual_limit_battery = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_battery.add((- model.dual_limit_battery[i])*(model.capacity_battery[i]-model.energy_battery[i]) == 0)
        
        model.con_cs_energy_buy = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_buy.add(model.energy_buy[i]*(Cost_buy-model.dual_eq_demand[i]) == 0)

        model.con_cs_energy_sell = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_sell.add(model.energy_sell[i]*(model.dual_eq_demand[i]-Cost_sell) == 0)
        
        model.con_cs_energy_battery_out = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_out.add(model.energy_battery_out[i]*(model.dual_eq_battery[i]-model.dual_eq_demand[i]) == 0)
        
        model.con_cs_energy_battery_in = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery_in.add(model.energy_battery_in[i]*(model.dual_eq_demand[i] - model.dual_eq_battery[i]) == 0)
        
        model.con_cs_energy_battery = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_battery.add(model.energy_battery[i]*(model.dual_eq_battery[i] - model.dual_limit_battery[i]) == 0)
        
        model.con_cs_energy_PV = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_PV.add(model.energy_PV[i]*(- model.dual_eq_demand[i] - model.dual_limit_PV[i]) == 0)
        
class FortunyKKT(BaseKKT):
    def __init__(self, settings: dict[str, int | float], PV_availability: list[float], Demand: list[float]):
        super().__init__(settings, PV_availability, Demand)
        model = self.model
        Cost_buy = self.settings["Cost_buy"]
        Cost_sell = self.settings["Cost_sell"]
        M = float("inf") # it should be changed

        # Binary variables
        model.binary_dual_limit_PV = pyo.Var(model.T, within=pyo.Binary)
        model.binary_dual_limit_battery = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_buy = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_sell = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_battery_out = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_battery_in = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_battery = pyo.Var(model.T, within=pyo.Binary)
        model.binary_energy_PV = pyo.Var(model.T, within=pyo.Binary)

        # complementary slackness
        model.con_cs_dual_limit_PV_A = pyo.ConstraintList()
        model.con_cs_dual_limit_PV_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_PV_A.add((- model.dual_limit_PV[i]) <= M*model.binary_dual_limit_PV[i])
            model.con_cs_dual_limit_PV_B.add((model.capacity_PV[i]-model.energy_PV[i]) <= M*(1-model.binary_dual_limit_PV[i]))
        
        model.con_cs_dual_limit_battery_A = pyo.ConstraintList()
        model.con_cs_dual_limit_battery_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_dual_limit_battery_A.add((- model.dual_limit_battery[i]) <= M*model.binary_dual_limit_battery[i])
            model.con_cs_dual_limit_battery_B.add( model.capacity_battery[i]-model.energy_battery[i] <= M*(1-model.binary_dual_limit_battery[i]) )
        
        model.con_cs_energy_buy_A = pyo.ConstraintList()
        model.con_cs_energy_buy_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_buy_A.add(model.energy_buy[i] <= M*model.binary_energy_buy[i])
            model.con_cs_energy_buy_B.add((Cost_buy-model.dual_eq_demand[i]) <= (1-M*model.binary_energy_buy[i]))

        model.con_cs_energy_sell_A = pyo.ConstraintList()
        model.con_cs_energy_sell_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_sell_A.add(model.energy_sell[i] <= M*model.binary_energy_sell[i])
            model.con_cs_energy_sell_B.add((model.dual_eq_demand[i]-Cost_sell) <= M*(1-model.binary_energy_sell[i]))

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
            model.con_cs_energy_battery_A.add(model.energy_battery[i] <= M*model.binary_eneregy_battery[i])
            model.con_cs_energy_battery_B.add((model.dual_eq_battery[i] - model.dual_limit_battery[i]) <= M*(1-model.binary_eneregy_battery[i]))
        
        model.con_cs_energy_PV_A = pyo.ConstraintList()
        model.con_cs_energy_PV_B = pyo.ConstraintList()
        for i in model.T:
            model.con_cs_energy_PV_A.add(model.energy_PV[i] <= M*model.binary_energy_PV[i])
            model.con_cs_energy_PV_B.add((- model.dual_eq_demand[i] - model.dual_limit_PV[i]) <= M*(1-model.binary_energy_PV[i]))
        

