import csv
import random 
import time
import math

import pandas as pd
import numpy as np 

def time_measure(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        print ('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed

#For testing the performance, comment in the decorator to measure time for execution
@time_measure
def augment_trajectory(df, aug_factor=0.3): 
    '''Augment a trajectory by moving certain pixels which are detections
    into random directions
    '''
    
    
    #Get list of indices and sample subset 
    indices = get_indices_detections(df)
    indices_sampled = random.sample(indices, math.ceil(len(indices) * aug_factor))
    random.shuffle(indices_sampled)

    for index_tuple in indices_sampled:
        new_dest = get_destination(df, index_tuple, indices)
        df = move_pixel(df, index_tuple, new_dest)
    
    return df


def get_destination(df, old_position, indices): 
    directions = [(0, -1), (0, 1), (1, 0), (-1, 0)]
    for _ in range(len(directions)):
        direction = random.sample(directions, 1)[0]

        x = old_position[0] + direction[0]
        y = old_position[1] + direction[1]
        new_pos = (x, y)

        if (new_pos[0] < 0) or (new_pos[0] > df.shape[0])\
        or (new_pos[1] < 0) or (new_pos[1] > df.shape[1]):
            continue

        if new_pos not in indices:
            return new_pos

    #if all position are already a detection pixel, return the old value
    return old_position


def get_indices_detections(df):
    detection_indices = list()
    for i_row in range(df.shape[0]):
        for i_col in range(df.shape[1]):
            if df.iloc[i_row, i_col] > 0.1:
                detection_indices.append((i_row, i_col))

    return detection_indices


def move_pixel(df, old_dest, new_dest):

    save_val = df.iloc[old_dest[0], old_dest[1]].copy()
    df.iloc[old_dest[0], old_dest[1]] = 0
    df.iloc[new_dest] = save_val

    return df

def main():
    test_df = pd.DataFrame(np.random.randint(0,100, size=(10, 10)), columns=None)
    test_df /= 100

    print(test_df.head())
    df_augmented = augment_trajectory(test_df)
    print(df_augmented.head())

if __name__ == '__main__':
    main()
