'''
Created on Apr 10, 2020

@author: jhkwakkel
'''
from ema_workbench import (RealParameter, TimeSeriesOutcome,
                           SequentialEvaluator, ema_logging)
    
from linnyr_connector import LinnyRModel  # @UnresolvedImport

if __name__ == '__main__':
    ema_logging.log_to_stderr(ema_logging.INFO)
    
    model = LinnyRModel(name = 'Smoothiemodel', wd='./model', 
                        model_file='simple_model.lnr')
    
    model.uncertainties = [RealParameter('Oranges:Price', 5, 20),
                           RealParameter('Apples:Price', 30, 40)]
    
    model.outcomes = [TimeSeriesOutcome('Apple price'),
                      TimeSeriesOutcome('Orange price')]
    
    with SequentialEvaluator(model) as evaluator:
        experiments, outcomes = evaluator.perform_experiments(scenarios=100)