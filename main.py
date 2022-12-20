
from model import HouseModel
from kkt import FortunyKKT
import numpy as np

Default_Settings = {
    "Lifetime": 10,  # Years
    "Cost_PV": 1000,  # €/kW
    "Cost_Battery": 300,  # €/kWh
    "Cost_buy": 0.25,  # €/kWh
    "Sell_price": 0.05,  # €/kWh
    "Demand_total": 3500,  # kWh/Year
}

settings = {
    "Lifetime": 10,  # Years
    "Cost_PV": 1000,  # €/kW
    "Cost_Battery": 300,  # €/kWh
    "Cost_buy": 0.25,  # €/kWh
    "Sell_price": 0.05,  # €/kWh
    "Demand_total": 3500,  # kWh/Year
}
PV_availability = np.loadtxt("data/TS_PVAvail.csv")
Demand = np.loadtxt("data/TS_Demand.csv")
model = HouseModel(settings, PV_availability, Demand)
model = FortunyKKT(settings, PV_availability, Demand)
model.solve()
output = model.get_output()
# for v in output:
#     print(v)


# print output
# print("Capacity for the PV module: " + str(pyo.value(solution.CapacityPV)) + " kW")
# print("Capacity for the battery module: " + str(pyo.value(solution.CapacityBattery)) + " kWh")

# cost_PV_year = settings["cost_PV"] / settings["lifetime"]
# cost_BAT_year = settings["cost_Battery"] / settings["lifetime"]
# print("\nCost of PV module per year: " + str(cost_PV_year) + " €")
# print("Cost of battery module per year: " + str(cost_BAT_year) + " €")
# print(
#     "CapEx per year: "
#     + str(cost_PV_year * pyo.value(solution.CapacityPV) + cost_BAT_year * pyo.value(solution.CapacityBattery))
#     + " €"
# )

# print("\nExecution of the model took " + str(round(end - start, 2)) + " seconds")