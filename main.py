
from model import HouseModel, Settings
from kkt import DualModel, BigM_KKT
import numpy as np

settings = Settings(
    Lifetime = 12*10,
    Price_PV = 1000,
    Price_battery= 300,
    Cost_buy = 0.25,
    Sell_price = 0.05,
    Demand_total = 3500
)

PV_availability = np.loadtxt("data/TS_PVAvail.csv")
Demand = np.loadtxt("data/TS_Demand.csv")
PV_availability = PV_availability[0:720]
Demand = Demand[0:720]
# model = HouseModel(settings, PV_availability, Demand)
# model = DualModel(settings, PV_availability, Demand)
model = BigM_KKT(settings, PV_availability, Demand)
model.solve()
output = model.get_output()
print(output.variables["capacity_battery"])
