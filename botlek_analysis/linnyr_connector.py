#!/usr/bin/env python
# coding: utf-8

# In[3]:


'''
Created on Apr 15, 2020

@author: Rob Roos

'''

# import required packages
import csv, subprocess, os
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
        with open(self.experiment_file, 'w', newline = '') as fh:
            
            # define the csv writer
            w = csv.writer(fh, delimiter = ';')
            
            # write the variables names to the first row
            w.writerow(experiment.keys())
            
            # create a list of values where if item not already a list, make it a list (paramount for zip_longest function)
            values = [[i] if isinstance(i,list) == False else i for i in experiment.values()]
            
            # write the transposed values list to the next rows (works for timeseries and accounts for empty cells)
            w.writerows(zip_longest(*values, fillvalue = ''))
            
        # define the file of the model object and strip off '.lnr' part so Linny-R can find it        
        modelfile = os.path.abspath(self.model_file)[:-4]

        # execute Linny-R console using the experiment input file
        subprocess.call([self.linnyr, modelfile, self.experiment_file])

        # locate and define the output file
        outputfile = f'{modelfile}_exp.csv'
        
        # read the data from the output file into a dataframe
        data = pd.read_csv(outputfile, delimiter = ';', decimal=',')
                         
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
        os.remove(self.experiment_file)

        # delete the output files (if things dont work out, have a look at the log file)
        os.remove(f'{modelfile}_exp.csv')
        os.remove(f'{modelfile}_exp.lp')
        os.remove(f'{modelfile}_exp.log')

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
    
        # import reference scenarios from the electricity market data as lists
        data_path = os.path.join(os.path.abspath('./data'), 'electricity_data.csv')
        electricity_data = pd.read_csv(data_path)
        upward_price_ref = list(electricity_data['invoeden_EURMWh'])
        downward_price_ref = list(electricity_data['afnemen_EURMWh'])
        imbalance_demand_ref = list(electricity_data['imbalance_demand']/1000)
        imbalance_supply_ref = list(electricity_data['imbalance_supply']/1000)

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
                               'CO2 EUROPEAN EMISSION ALLOWANCES:Price':25,
                               'H2 markt:Price':0.107,
                               'NaOH 50%:Price':200}

        # set the number of time steps
        self.time_steps = 35040
    
    # define a function for running an experiment
    def run_experiment(self, experiment):
            
        # modify the sampled experiment data accordingly
        for i in experiment.keys():
            if i in self.reference_time_series.keys():
                experiment[i] = [ experiment[i] * x for x in self.reference_time_series[i] ]
            elif i in self.current_values.keys():
                current_value = self.current_values[i]
                future_value = experiment[i]
                gradient =  (future_value - current_value) / self.time_steps
                experiment[i] = [ gradient * x + current_value for x in range(self.time_steps + 1) ]
            else:
                continue
        
        # let the base class (generic Linny-R connector) run an experiment using this modified data
        return super().run_experiment(experiment)


# In[ ]:




