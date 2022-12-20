
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