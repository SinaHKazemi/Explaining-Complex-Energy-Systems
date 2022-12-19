# Explaining-Complex-Energy-Systems

## Introduction
The code presented here is part of the "Explaining Complex Energy Systems: A Challenge" poster presented on the "Tackling Climate Change with Machine Learning"-Workshop at the NIPS 2020.
We believe, that the field of explainable AI can help creating better explanations for energy system design tools.
This could make such tool more accessible for non-experts, helping them to understand the impact of technologies on the climate change as well their costs.

In this repository we provide a simple energy system model in the form of a linear program, written in Python Pyomo.
The linear program can be found in **Model.py**. 
In **solverSettings.txt** the used solver and additional options can be defined. 
An overview of ways to interact with the model is given in **ExampleRun.py**.

## LP Model
The linear program implemented in **Model.py** has the following minimization goal:

$\min\limits_{Cap,p} cost = c_{PV} \times Cap_{PV}  c_{battery} \times Cap_{battery}^S  \sum_{t} c_{buy}(t) \times p_{buy}(t)$

The following restrictions are applied:

<img src="https://render.githubusercontent.com/render/math?math=p_{buy}(t) %2B p_{PV}(t) %2B p_{battery}^{out}(t) - p_{battery}^{in}(t) = Demand(t), \forall t">

<img src="https://render.githubusercontent.com/render/math?math=p_{battery}^{S}(t) = p_{battery}^{S}(t-1) %2B p_{battery}^{in}(t) \times \delta t - p_{battery}^{out}(t) \times \delta t , t \in 2,...,T">

<img src="https://render.githubusercontent.com/render/math?math=0 \leq p_{PV}(t) \leq Cap_{PV} \times availibilty_{PV}(t) \times \delta t, \forall t">

<img src="https://render.githubusercontent.com/render/math?math=0 \leq p_{battery}^{S}(t) \leq Cap_{battery}^S, \forall t">

<img src="https://render.githubusercontent.com/render/math?math=p_{battery}^{S}(0) = p_{battery}^{S}(T)">
  
<img src="https://render.githubusercontent.com/render/math?math=0 \leq p_{buy}(t), \forall t">

## Time series
* **Demand time series** - distribution of 8760 values that sum up to 1
  * Data is for the residential_building_1 for the year 2016 from [Open Power System Data](https://data.open-power-system-data.org/household_data/2020-04-15)
* **Photovoltaic availability** - values between 0 and 1 for each of the 8760 hours of a year, while 1 is a 100% yield of the installed capacity and 0 is no energy production
  * Data is for the city Darmstadt in Germany from [Renewables.ninja](https://www.renewables.ninja/)

## Authors
* [Jonas H&uuml;lsmann](https://www.eins.tu-darmstadt.de/eins/team/jonas-huelsmann)
* [Florian Steinke](https://www.eins.tu-darmstadt.de/eins/team/florian-steinke)
