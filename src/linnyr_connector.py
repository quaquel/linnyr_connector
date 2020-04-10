'''
Created on Apr 10, 2020

@author: jhkwakkel
'''
# import required stuff from the EMA Workbench

import csv
from itertools import zip_longest
import subprocess, os

import numpy as np
import pandas as pd

from ema_workbench.em_framework.model import FileModel, SingleReplication
from ema_workbench.util.ema_logging import method_logger


# define a base class for interacting with Linny-R models
class BaseLinnyRModel(FileModel):
    
    # create an instance of this class
    def __init__(self, name, wd=None, model_file=None):
        super().__init__(name, wd, model_file)
        

        self.experiment_file = 'exp.csv'
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
            w.writerows([list(filter(None,i)) for i in zip_longest(*values)])

        # execute Linny-R console using the experiment input file
        # define the file of the model object and strip off '.lnr' part so Linny-R can find it
        modelfile = os.path.join(self.working_directory, self.model_file)[:-4]
        
        subprocess.call([self.linnyr, modelfile, self.experiment_file])

        # read the csv output file from Linny-R and transpose it
        
        outputfile = f'{modelfile}_exp.csv'
        
        csv_reader = zip(*csv.reader(open(outputfile), delimiter=';'))

        # create empty dictionary for the results
        results = {}

        # loop through the rows containing variable name and values per time step ('variable','2','5','4')
        for row in csv_reader:

            # skip the first row containing the time step variable
            if row[0] == 'T':
                continue

            # create an empty list to store the values in
            values = []

            # loop through the items in each row
            for i in row:

                # try to append the item as a float to the value list
                try:
                    values.append(float(i))

                # if this rases an error, it is the first item containing the variable name
                except:
                    variable_name = i

            # append the dictionary with key = variable_name and value = values
            results[variable_name] = tuple(values)

        # delete the csv input file
        # os.remove(f'exp.csv')

        # delete the output files (if things dont work out, have a look at the log file)
        os.remove(f'{modelfile}_exp.csv')
        os.remove(f'{modelfile}_exp.lp')
        os.remove(f'{modelfile}_exp.log')

        # return the results
        return results


class LinnyRModel(SingleReplication, BaseLinnyRModel):
    pass