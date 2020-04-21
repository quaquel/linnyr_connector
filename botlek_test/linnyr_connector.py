#!/usr/bin/env python
# coding: utf-8

# In[2]:


'''
Created on Apr 15, 2020

@author: Rob Roos

'''

# import required packages
import csv, subprocess, os, copy
import pandas as pd
from itertools import zip_longest
from ema_workbench.em_framework.model import FileModel, SingleReplication
from ema_workbench.util.ema_logging import method_logger

# define a base class for interacting with Linny-R models
class BaseLinnyRModel(FileModel):
    
    # create an instance of this class
    def __init__(self, name, wd=None, model_file=None):
        
        # inherit properties from the base class
        super().__init__(name, wd, model_file)
        
        # define a name for the experiment file
        self.experiment_file = 'exp.csv'
        
        # define the path of the Linny-R executable
        self.linnyr = os.path.join(os.path.abspath('./software'), 'lrc.exe')
        
    # define a function for running an experiment
    @method_logger(__name__)
    def run_experiment(self, experiment):
        
        # create a csv input file readable by Linny-R from the experiment dict
        with open(os.path.join(self.working_directory, self.experiment_file), 'w', newline = '') as fh:
            
            # define the csv writer
            w = csv.writer(fh, delimiter = ';')
            
            # write the variables names to the first row
            w.writerow(experiment.keys())
            
            # create a list of values where if item not already a list, make it a list (paramount for zip_longest function)
            values = [[i] if isinstance(i,list) == False else i for i in experiment.values()]
            
            # write the transposed values list to the next rows (works for timeseries and accounts for empty cells)
            w.writerows(zip_longest(*values, fillvalue = ''))
            
        # define the file of the model object and strip off '.lnr' part so Linny-R can find it        
        modelfile = self.model_file[:-4]

        # save the path of the current working directory as a variable
        curdir = os.getcwd()

        # temporarily change the working directory to the model folder
        os.chdir(self.working_directory)

        # execute Linny-R console using the experiment input file
        subprocess.call([self.linnyr, modelfile, self.experiment_file])

        # change the working directory back to the orginal
        os.chdir(curdir)

        # locate and define the output file
        outputfile = os.path.join(self.working_directory, f'{modelfile}_exp.csv')
        
        # read the data from the output file into a dataframe
        data = pd.read_csv(outputfile, delimiter=';', decimal=',')
                         
        # create an empty dictionary for the results
        results = {}
                         
        # loop trough the output variables                
        for i in data.columns:
                         
            # skip the time variable           
            if i == 'T':
                continue
                         
            # fill in the dictionary with the values in a tuple         
            else:
                results[i] = tuple(data[i])
                
        # delete the csv input file
        os.remove(os.path.join(self.working_directory, self.experiment_file))

        # delete the output files (if things dont work out, have a look at the log file)
        os.remove(os.path.join(self.working_directory, f'{modelfile}_exp.csv'))
        os.remove(os.path.join(self.working_directory, f'{modelfile}_exp.lp'))
        os.remove(os.path.join(self.working_directory, f'{modelfile}_exp.log'))

        # return the results
        return results

# define the base class
class LinnyRModel(SingleReplication, BaseLinnyRModel):
    pass

# extension (subclass) of Linny-R connector class, specifically for the Thesis of Rob Roos (2020)
class LinnyRModel_Botlek(LinnyRModel):
    
    # create an instance of this class
    def __init__(self, name, wd=None, model_file=None):
        
        # inherit properties from the base class (the generic Linny-R connector)
        super().__init__(name, wd, model_file)
        
        # specify the time horizon in years
        self.time_horizon = 10

        # define the number of time steps (quarters) in that time horizon
        self.time_steps = 35040 * self.time_horizon
    
        # import electricity market reference scenarios as lists and multiply by 10 (years)
        data_path = os.path.join(os.path.abspath('./data'), 'electricity_data.csv')
        electricity_data = pd.read_csv(data_path)
        upward_price_ref = list(electricity_data['invoeden_EURMWh'])*self.time_horizon
        downward_price_ref = list(electricity_data['afnemen_EURMWh'])*self.time_horizon
        imbalance_demand_ref = list(electricity_data['imbalance_demand']/1000)*self.time_horizon
        imbalance_supply_ref = list(electricity_data['imbalance_supply']/1000)*self.time_horizon

        # insert the first number as a default value at the beginning of the list (for Linny-R specific input)
        upward_price_ref.insert(0, upward_price_ref[0])
        downward_price_ref.insert(0, downward_price_ref[0])
        imbalance_demand_ref.insert(0, imbalance_demand_ref[0])
        imbalance_supply_ref.insert(0, imbalance_supply_ref[0])

        # create a dictionary for the time serie reference scenarios
        self.reference_time_series = {'Unbal opregelen:Price':upward_price_ref, 
                                      'Unbal afregelen:Price':downward_price_ref,
                                      'Unbal afregelen:LB':imbalance_supply_ref,
                                      'Unbal opregelen:UB':imbalance_demand_ref}

        # create a dictionary for current values
        self.current_values = {'E day-ahead:Price':57,
                               'natural gas market:Price':0.28,
                               'CO2 EUROPEAN EMISSION ALLOWANCES:StC':25,
                               'H2 markt:Price':0.107,
                               'NaOH 50%:Price':200}
        
        # create a list with the constants
        self.constant_list = ['Capex E-boiler:Price', 'OPEX E-BOILER:Price', 'CAPEX Steam Pipe:Price']
    
    # define a function for running an experiment
    def run_experiment(self, experiment):
        
        # deep copy the experiment dict
        experiment = copy.deepcopy(experiment)
        
        # create an empty dict for the lever values
        d = {}
        
        # modify the sampled experiment data accordingly
        for i in experiment.keys():
            
            # if the variable is a factor to establish time series (electricity data)
            if i in self.reference_time_series.keys():
                experiment[i] = [ experiment[i] * x for x in self.reference_time_series[i] ]
                
            # if the variable is the future value in 2030 to calculate gradient for linear function
            elif i in self.current_values.keys():
                current_value = self.current_values[i]
                future_value = experiment[i]
                gradient =  (future_value - current_value) / self.time_steps
                experiment[i] = [ gradient * x + current_value for x in range(self.time_steps + 1) ]
                
            # if the variable is a constant (CAPEX, OPEX)
            elif i in self.constant_list:
                continue
                
            # if the variable is the Steam Pipe alternative boolean
            elif i == 'steam_pipe':
                if experiment[i] == True:
                    d['Option: transport to Nouryon (Steam pipe owner):UB'] = 7.5
                    d['FUTURE: transport 5210 site (Steam pipe owner):UB'] = 30
                    d['Financiering Steam Pipe (Steam pipe owner):UB'] = 55
                else:
                    d['Option: transport to Nouryon (Steam pipe owner):UB'] = 0
                    d['FUTURE: transport 5210 site (Steam pipe owner):UB'] = 0
                    d['Financiering Steam Pipe (Steam pipe owner):UB'] = 0
                    
            # if the variable is the E-boiler alternative boolean
            elif i == 'e_boiler':
                if experiment[i] == True:
                    d['Electrode boiler 50 bar 2/7 aFRR (Air Liquide):UB'] = 5
                    d['electrode boiler 50 bar 5/7 inzetbaar (Air Liquide):UB'] = 17.5
                    d['by-pass aFRR (ghost actor):UB'] = 0
                    d['AL 50 bar fixed rate (Air Liquide):LB'] = 22.5
                    d['AL 50 bar fixed rate (Air Liquide):UB'] = 22.5
                    d['DA inkoop EB70 (Air Liquide):UB'] = 6
                else:
                    d['Electrode boiler 50 bar 2/7 aFRR (Air Liquide):UB'] = 0
                    d['electrode boiler 50 bar 5/7 inzetbaar (Air Liquide):UB'] = 0
                    d['by-pass aFRR (ghost actor):UB'] = 5
                    d['AL 50 bar fixed rate (Air Liquide):LB'] = 0
                    d['AL 50 bar fixed rate (Air Liquide):UB'] = 0
                    d['DA inkoop EB70 (Air Liquide):UB'] = 0
                    
            # if the variable is the Chlorine Storage alternative boolean
            elif i == 'chlorine_storage':
                if experiment[i] == True:
                    d['stored CL2 (Nouryon):UB'] = 3200
                else:
                    d['stored CL2 (Nouryon):UB'] = 1600
        
        # delete the now useless lever variables
        experiment.pop('steam_pipe')
        experiment.pop('e_boiler')
        experiment.pop('chlorine_storage')

        # merge the experiment dict with the level dict
        experiment = {**experiment, **d}
        
        # let the base class (generic Linny-R connector) run an experiment using this modified data and return results
        return super().run_experiment(experiment)

