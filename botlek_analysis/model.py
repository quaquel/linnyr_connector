
from ema_workbench import (RealParameter,
                           CategoricalParameter,
                           TimeSeriesOutcome,
                           Policy,
                           MultiprocessingEvaluator,
                           SequentialEvaluator, 
                           ema_logging)

from linnyr_connector import LinnyRModel_Botlek #@UnresolvedImport

import os

# define a function for generating policies
def generate(name, steam_pipe, e_boiler, chorine_storage):
    
    d = {}
    
    if steam_pipe == True:
        d['Steam Pipe to Nouryon'] = 7.5
        d['Steam Pipe to Air Liquide and Huntsman'] = 30
    else:
        d['Steam Pipe to Nouryon'] = 0
        d['Steam Pipe to Air Liquide and Huntsman'] = 0
    if e_boiler == True:
        d['E-boiler 1'] = 5
        d['E-boiler 2'] = 17.5
        d['E-boiler 3'] = 0
        d['E-boiler 4'] = 22.5
        d['E-boiler 5'] = 6
    else:
        d['E-boiler 1'] = 0
        d['E-boiler 2'] = 0
        d['E-boiler 3'] = 1000
        d['E-boiler 4'] = 0
        d['E-boiler 5'] = 0
    if chorine_storage == True:
        d['Chlorine storage'] = 3200
    else:
        d['Chlorine storage'] = 1600
        
    return Policy(name, **d)
    


if __name__ == '__main__':
        
    # enable info logging
    ema_logging.log_to_stderr(ema_logging.INFO)
    
    # define the model
    model = LinnyRModel_Botlek(name='BotlekModel', wd='./model',
                               model_file='botlek_model.lnr')
    
    # define the uncertain factors
    model.uncertainties = [RealParameter(name = 'Electricity price in 2030',
                                         variable_name = 'E day-ahead:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'Gas price in 2030',
                                         variable_name = 'natural gas market:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'CO2 emission price in 2030', # negative values
                                         variable_name = 'CO2 EUROPEAN EMISSION ALLOWANCES:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'Hydrogen price in 2030',
                                         variable_name = 'H2 markt:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'NaOH 50% price in 2030',
                                         variable_name = 'NaOH 50%:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'Factor upward balancing electricity price',
                                         variable_name = 'Unbal opregelen:Price',
                                         lower_bound = 0.7, 
                                         upper_bound = 1.3),
                           RealParameter(name = 'Factor downward balancing electricity price',
                                         variable_name = 'Unbal afregelen:Price',
                                         lower_bound = 0.7, 
                                         upper_bound = 1.3),
                           RealParameter(name = 'Factor electricity supply imbalance market',
                                         variable_name = 'Unbal afregelen:LB',
                                         lower_bound = 0.7, 
                                         upper_bound = 1.3),
                           RealParameter(name = 'Factor electricity demand imbalance market',
                                         variable_name = 'Unbal opregelen:UB',
                                         lower_bound = 0.7, 
                                         upper_bound = 1.3),
                           RealParameter(name = 'E-boiler CAPEX', # per quarter
                                         variable_name = 'Capex E-boiler:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'E-boiler OPEX', # per quarter
                                         variable_name = 'OPEX E-BOILER:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0),
                           RealParameter(name = 'Steam Pipe CAPEX',
                                         variable_name = 'CAPEX Steam Pipe:Price',
                                         lower_bound = 5.0, 
                                         upper_bound = 20.0)]
    
    # define the levers (Power-to-X alternatives)
    model.levers = [CategoricalParameter(name = 'Steam Pipe to Nouryon',
                                         variable_name = 'Option: transport to Nouryon (Steam pipe owner):UB',
                                         categories = [0, 7.5]),
                    CategoricalParameter(name = 'Steam Pipe to Air Liquide and Huntsman',
                                         variable_name = 'FUTURE: transport 5210 site (Steam pipe owner):UB',
                                         categories = [0, 30]),
                    CategoricalParameter(name = 'E-boiler 1',
                                         variable_name = 'Electrode boiler 50 bar 2/7 aFRR (Air Liquide):UB',
                                         categories = [0, 5]),
                    CategoricalParameter(name = 'E-boiler 2',
                                         variable_name = 'electrode boiler 50 bar 5/7 inzetbaar (Air Liquide):UB',
                                         categories = [0, 17.5]),
                    CategoricalParameter(name = 'E-boiler 3',
                                         variable_name = 'by-pass aFRR (ghost actor):UB',
                                         categories = [1000, 0]),
                    CategoricalParameter(name = 'E-boiler 4',
                                         variable_name = 'AL 50 bar fixed rate (Air Liquide):LB',
                                         categories = [0, 22.5]),
                    CategoricalParameter(name = 'E-boiler 5',
                                         variable_name = 'DA inkoop EB70 (Air Liquide):UB',
                                         categories = [0, 6]),
                    CategoricalParameter(name = 'Chlorine storage',
                                         variable_name = 'stored CL2 (Nouryon):UB',
                                         categories = [1600, 3200])]
    
    # define the outcomes
    model.outcomes = [TimeSeriesOutcome(name = 'CF total',
                                        variable_name = 'CF total' ),
                      TimeSeriesOutcome(name = 'CO2 emissions',
                                        variable_name = 'CO2 emission')]
    

    # generate the desired policies
    policies = [generate(name = 'no policy', steam_pipe=False, e_boiler=False,
                         chorine_storage=False),
                generate(name='Only Steam Pipe', steam_pipe=True,
                         e_boiler=False, chorine_storage=False),
                generate(name='Only E-boiler', steam_pipe=False, e_boiler=True,
                         chorine_storage=False),
                generate(name='Only Chlorine storage', steam_pipe=False, 
                         e_boiler = False, chorine_storage = True),
                generate(name='Steam Pipe & E-boiler', steam_pipe=True,
                         e_boiler=True, chorine_storage=False),
                generate(name='Steam Pipe & Chlorine storage',
                         steam_pipe=True, e_boiler=False, chorine_storage=True),
                generate(name='E-boiler & Chlorine storage', steam_pipe=False,
                         e_boiler=True, chorine_storage=True),
                generate(name='All options', steam_pipe=True, e_boiler=True,
                         chorine_storage=True)]
    
    # run the analysis
    with SequentialEvaluator(model) as evaluator:
        experiments, outcomes = evaluator.perform_experiments(policies=policies,
                                                              scenarios=1)
        
    print(experiments)