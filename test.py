import pyomo.environ as pyo

model = pyo.ConcreteModel()

model.x = pyo.Var([1,2], domain=pyo.NonNegativeReals)

model.OBJ = pyo.Objective(expr = 2*model.x[1] + 3*model.x[2])

model.Constraint1 = pyo.Constraint(expr = 3*model.x[1] + 4*model.x[2] >= 1)
# x = pyo.Set([model.x[1], model.x[2]])
model.s = pyo.SOSConstraint(var = [model.x[1], model.x[2]], sos=1)
model.pprint()
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
# solver = SolverFactory("cplex")
# solver_output = solver.solve(model, tee = True)