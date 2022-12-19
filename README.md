# Explaining-Complex-Energy-Systems

## Introduction
The code presented here is part of the "Explaining Complex Energy Systems: A Challenge" poster presented on the "Tackling Climate Change with Machine Learning"-Workshop at the NIPS 2020.
We believe, that the field of explainable AI can help creating better explanations for energy system design tools.
This could make such tool more accessible for non-experts, helping them to understand the impact of technologies on the climate change as well their costs.

In this repository we provide a simple energy system model in the form of a linear program, written in Python Pyomo.
The linear program can be found in **Model.py**. 
In **solverSettings.txt** the used solver and additional options can be defined. 
An overview of ways to interact with the model is given in **ExampleRun.py**.

## Quick Start
1. install python 3.11
2. build a new virtual environment and activate it
```console
> python -m venv env
> env\Scripts\activate
```
3. install required packages
```console
> pip install -r requirements.txt
```
4. run main.py
```console
> python main.py
```


## Time series
* **Demand time series** - distribution of 8760 values that sum up to 1
  * Data is for the residential_building_1 for the year 2016 from [Open Power System Data](https://data.open-power-system-data.org/household_data/2020-04-15)
* **Photovoltaic availability** - values between 0 and 1 for each of the 8760 hours of a year, while 1 is a 100% yield of the installed capacity and 0 is no energy production
  * Data is for the city Darmstadt in Germany from [Renewables.ninja](https://www.renewables.ninja/)

## Authors
* [Sina Hajikazemi](https://www.eins.tu-darmstadt.de/eins/team/sina-hajikazemi)
* [Jonas H&uuml;lsmann](https://www.eins.tu-darmstadt.de/eins/team/jonas-huelsmann)
* [Florian Steinke](https://www.eins.tu-darmstadt.de/eins/team/florian-steinke)
