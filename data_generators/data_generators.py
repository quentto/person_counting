import sys
import os 
import pandas as pd
import numpy as np
import math
import abc
from random import shuffle

from tensorflow import keras
from sklearn.model_selection import train_test_split

from person_counting.utils import scaler
from person_counting.models.model_argparse import parse_args

LABEL_HEADER = ['file_name', 'entering', 'exiting', 'video_type']

np.random.seed(42)

class Generator_CSVS(keras.utils.Sequence):
    '''Abstract class for Generators to load csv files from 
    video folder structre like PCDS Dataset
    '''
    __metaclass__ = abc.ABCMeta

    def __init__(self,
                 length_t,
                 length_y,
                 file_names,
                 filter_cols,
                 filter_rows_factor,
                 batch_size, 
                 top_path,
                 label_file): 
        ''' Initialize Generator object.

            Arguments
                length_t            : Length of the feature's DataFrame in time dimension
                length_y            : Length of the feature's DataFrame in y direction
                file_names          : File names to be processed
                filter_cols,        : Amount of columns to be filtered at end and start of DataFrame
                filter_rows_factor  : Factor of rows to be filtered
                batch_size          : Batch size
                top_path            : Parent path where csv files are contained
                label_file          : Name of the label file
        '''

        self.top_path               = top_path
        self.label_file             = label_file
        self.length_t               = length_t
        self.length_y               = length_y
        self.file_names             = file_names 
        self.filter_cols            = filter_cols
        self.filter_rows_factor     = filter_rows_factor
        self.batch_size             = batch_size
        self.labels                 = list()
        self.scaler                 = scaler.CSVScaler(top_path, label_file, file_names)
        self.df_y                   = pd.read_csv(self.top_path + self.label_file, header=None, names=LABEL_HEADER)

    @abc.abstractmethod
    def datagen(self):
        '''Returns datagenerator
        '''
        return

    def __len__(self):
        '''Returns the lenth of the datagen
        '''
        return int(np.ceil(len(self.file_names) / float(self.batch_size)))    
    
    def __getitem__(self, file_name):
        '''Gets pair of features and labels for given filename
        Arguments: 
            file_name: The name of the file which shall be parsed
        '''
        df_x = self.__get_features(file_name)
        #Only remove when index is saved in csv
        if check_for_index_col(self.top_path):
            df_x.drop(df_x.columns[0], axis=1, inplace=True)

        if df_x is not None:
            df_x = self.scaler.transform_features(df_x)

        label = get_entering(file_name, self.df_y)
        label = self.scaler.transform_labels(label)

        if (df_x is None) or (label is None): 
            raise FileNotFoundError('No matching csv for existing label, or scaling went wrong')

        df_x = clean_ends(df_x, del_leading=self.filter_cols, del_trailing=self.filter_cols)
        df_x = filter_rows(df_x, self.filter_rows_factor)
        assert df_x.shape[0] == (self.length_t)\
           and df_x.shape[1] == (self.length_y) 

        return df_x, label

    def __get_features(self, file_name): 
        '''Get sample of features for given filename. 

        Arguments: 
            file_name: Name of given training sample

            returns: Features for given file_name
        '''

        full_path = os.path.join(self.top_path, file_name)

        try:
            df_x = pd.read_csv(full_path, header=None)
            return df_x

        except Exception as e:
            # print('No matching file for label found, skip')
            return None

    def get_labels(self):
        '''Returns the labels which were yielded since calling reset_labels() 
        '''
        return np.array(self.labels)

    def reset_label_states(self): 
        '''Resets the labels which were processed
        '''
        self.labels = list()


def print_train_test_lengths(train_file_names, test_file_names, args):      
    '''Print out the length of training and test files which were loaded
    
    Arguments: 
        train_file_names: Names of training files 
        test_file_names: Names of test files
        args: Parsed args from command line
    '''  
    csv_names = list()
    for _, _, files in os.walk(args.top_path):
        csv_names = csv_names.extend(files)

    train_count = sum(el in csv_names for el in train_file_names)
    test_count =  sum(el in csv_names for el in test_file_names)
    print('Dataset contains: \n{} training csvs \n{} testing csvs'.format(train_count, test_count))
    

def check_for_index_col(top_path): 
    '''Returns true if index column in sample csv file exists

    Arguments: 
        top_path: Path where the csv files are contained in 
    '''

    for root, _, files in os.walk(top_path): 
        for file_name in files:
            if file_name[-4:] == '.csv' and not ('label' in file_name):
                full_path = os.path.join(root, file_name)
                df = pd.read_csv(full_path, header=None)
                for i in range(df.shape[0]):
                    if df.iloc[i, 0] != i:
                        return False
                return True


def split_files(args):
    ''' Splits all files in the training set into train and test files
    and returns lists of names for train and test files
    '''
    df_names = pd.read_csv(args.top_path + args.label_file).iloc[:,0]

    #replace .avi with .csv
    df_names = df_names.apply(lambda row: row[:-4] + '.csv')
    return train_test_split(df_names, test_size=0.25, random_state=42)
            

def get_filters(file_names):
    '''Searches for the right columns amount of columns and rows to drop
    '''
    #TODO: Implement. Now dummy function
    raise NotImplementedError


def get_entering(file_name, df_y): 
    ''' Get number of entering persons to existing training sample. 

    Arguments: 
        file_name: Name of given training sample
        df_y: Dataframe with all labels for all samples

        returns: Label for given features
    '''
    try: 
        entering = df_y.loc[df_y.file_name == file_name].entering
        return entering 

    except Exception as e:
        # print('No matching label found for existing csv file')
        return None


def get_exiting(file_name, df_y): 
    '''Get number of exiting persons to existing training sample. 

    Arguments: 
        file_name: Name of given training sample
        df_y: Dataframe with all labels for all samples

        returns: Exiting persons for given file
    '''
    try: 
        exiting = df_y.loc[df_y.file_name == file_name].exiting
        return exiting 

    except Exception as e:
        # print(e, ', no matching label found for existing csv file')
        return None
    


def clean_ends(df, del_leading=5, del_trailing=5):
    ''' Delete leading and trailing columns due to sparsity. 

    Arguments: 
        df: Dataframe to adjust
        del_leading: Number of leading columns to delete
        del_trailing: Number of trailing columns to delete
        
    returns: Dataframe with cleaned columns
    '''

    for i in range(del_leading):
        df.drop(df.columns[i], axis=1, inplace=True)

    col_length = df.shape[1]

    for i in range(del_trailing):
        df.drop(df.columns[col_length - i - 1], axis=1, inplace=True)
    
    return df


def filter_rows(df, filter_rows_factor): 
    '''Filters rows according to the filter_rows_factor in a given DataFrame
    
    Arguments: 
        df: Dataframe which shall be filtered 
        filter_rows_factor: The factor which shall be used for filtering rows, 
                            a factor of 4 will remove 3/4 rows and keeps every
                            forth row, starting with the first row
        
        returns: Filtered Dataframe
    '''

    return df.iloc[::filter_rows_factor, :]


def get_lengths(top_path):
    '''returns: Number of timesteps, number of features (columns) which csv files have
    '''

    for root, _, files in os.walk(top_path): 
        for file_name in files:
            if file_name[-4:] == '.csv' and not ('label' in file_name):
                full_path = os.path.join(root, file_name)
                df = pd.read_csv(full_path, header=None)
                if check_for_index_col(top_path):
                    print('Warning: Index column existing, make sure to drop it!')
                    return df.shape[0], df.shape[1] - 1
                else: 
                    return df.shape[0], df.shape[1]


def get_filtered_lengths(args):
    '''Returns the length of the feature dataframes after filtering those with 
    the above given methods

    Arguments: 
        #TODO: Change args to meanningful variables
    '''

    timestep_num, feature_num = get_lengths(args.top_path)
    #TODO: Verify that the rounding is correct, maybe math.ceil() rounding in some cases has to be used

    if timestep_num % args.filter_rows_factor != 0:
        filtered_length_t = int(timestep_num / args.filter_rows_factor) + 1
    else: 
        filtered_length_t = int(timestep_num / args.filter_rows_factor) 

    filtered_length_y = feature_num - (2 * args.filter_cols)

    return filtered_length_t, filtered_length_y

