
from model import HouseModel, Settings
from kkt import FortunyKKT, BaseKKT
import numpy as np

settings_dict = {
    "Lifetime": 10 * 12,  # Years
    "Price_PV": 1000,  # €/kW
    "Price_battery": 300,  # €/kWh
    "Cost_buy": 0.25,  # €/kWh
    "Sell_price": 0.05,  # €/kWh
    "Demand_total": 3500,  # kWh/Year
}



settings = Settings(
    settings_dict["Lifetime"],
    settings_dict["Price_PV"],
    settings_dict["Price_battery"],
    settings_dict["Cost_buy"],
    settings_dict["Sell_price"],
    settings_dict["Demand_total"],
)

PV_availability = np.loadtxt("data/TS_PVAvail.csv")
Demand = np.loadtxt("data/TS_Demand.csv")
PV_availability = PV_availability[0:720]
Demand = Demand[0:720]
# model = HouseModel(settings, PV_availability, Demand)
# model = BaseKKT(settings, PV_availability, Demand)
model = FortunyKKT(settings, PV_availability, Demand)
model.solve()
output = model.get_output()
print(output["capacity_battery"])
print(output["dual_obj"])


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