import os 
import pandas as pd
import numpy as np
import math
from random import shuffle

from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler

from person_counting.data_generators.data_generators import Generator_CSVS
from person_counting.data_generators.data_generators import *
from person_counting.utils.preprocessing import get_filtered_lengths
from person_counting.utils.scaler import FeatureScaler, LabelScaler
from person_counting.utils.preprocessing import apply_file_filters

class Generator_CSVS_CNN(Generator_CSVS):
    '''
    Generators class to load csv files from 
    video folder structre like PCDS Dataset and
    train CNNs

    Arguments (**kwargs)
        length_t            : Length of the feature's DataFrame in time dimension
        length_y            : Length of the feature's DataFrame in y direction
        file_names          : File names to be processed
        filter_cols_upper,  : Amount of columns to be filtered at end and start of DataFrame
        batch_size          : Batch size
        top_path            : Parent path where csv files are contained
        label_file          : Name of the label file

    '''

    def __init__(self, *args, **kwargs):
        super(Generator_CSVS_CNN, self).__init__(*args, **kwargs)


def create_datagen(top_path, 
                   sample, 
                   label_file, 
                   augmentation_factor=0, 
                   filter_hour_above=24, 
                   filter_category_noisy=False): 
    '''
    Creates train and test data generators for lstm network. 

    Arguments: 
        top_path: Parent directory where shall be searched for training files
        sample: sample of hyperparameters used in this run
        label_file: Name of the label file containing all the labels
        augmentation_factor: Factor how much augmentation shall be done, 1 means
                             moving every pixel for one position
        filter_hour_above: Hour after which videos shall be filtered
        filter_category_noisy: Flag if noisy videos shall be filtered
    '''
    #Load filenames and lengths
    length_t, length_y = get_filtered_lengths(top_path, sample)
    train_file_names, validation_file_names, test_file_names = split_files(top_path, label_file)

    #Apply filters
    train_file_names = apply_file_filters(train_file_names, filter_hour_above, filter_category_noisy)
    validation_file_names = apply_file_filters(validation_file_names, filter_hour_above, filter_category_noisy)
    test_file_names = apply_file_filters(test_file_names, filter_hour_above, filter_category_noisy)
    scale_files = pd.concat([train_file_names, validation_file_names, test_file_names])

    print('Dataset contains: \n{} training files \n{} validation files \n{} testing files'.format(len(train_file_names),
                                                                                                  len(validation_file_names),
                                                                                                  len(test_file_names)))
    
    feature_scaler = FeatureScaler(top_path, scale_files, sample)
    label_scaler = LabelScaler(top_path, label_file, scale_files, sample)

    gen_train = Generator_CSVS_CNN(length_t=length_t,
                                   length_y=length_y,
                                   file_names=train_file_names,
                                   feature_scaler=feature_scaler, 
                                   label_scaler=label_scaler, 
                                   sample=sample,
                                   top_path=top_path,
                                   label_file=label_file, 
                                   augmentation_factor=augmentation_factor)

    #Don't do augmentation here!
    gen_validation = Generator_CSVS_CNN(length_t=length_t,
                                  length_y=length_y,
                                  file_names=validation_file_names,
                                  feature_scaler=feature_scaler, 
                                  label_scaler=label_scaler,
                                  sample=sample,
                                  top_path=top_path,
                                  label_file=label_file, 
                                  augmentation_factor=0)

    gen_test = Generator_CSVS_CNN(length_t=length_t,
                                  length_y=length_y,
                                  file_names=test_file_names,
                                  feature_scaler=feature_scaler, 
                                  label_scaler=label_scaler,
                                  sample=sample,
                                  top_path=top_path,
                                  label_file=label_file, 
                                  augmentation_factor=0)
    
    return gen_train, gen_validation, gen_test

