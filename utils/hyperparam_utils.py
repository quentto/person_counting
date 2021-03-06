import os

import tensorflow as tf
import keras 
from tensorboard.plugins.hparams import api as hp
from datetime import datetime

from person_counting.bin.evaluate import Evaluate

def hard_tanh(x): 
    '''Hard tanh function
    Arguments: 
        x: Input value
    
    hard_tanh(x) = {-1,      for x < -2, 
                    tanh(x), for x > -2 and x < 2
                    1,       for x > 2              }

    returns value according to hard tanh function
    '''
    return tf.maximum(tf.cast(-1, tf.float32), tf.minimum(tf.cast(1, tf.float32), tf.cast(keras.backend.tanh(x) * 1.05, tf.float32)))

def get_optimizer(optimizer, learning_rate=1e-4):
    ''' Gets an keras optimizer and sets params 

    Arguments: 
        optimizer: Name of keras optimizer
        learning rate: Learning rate for training velocity

    returns Keras optimizer
    '''
    #TODO: For finetuning, more parameters (e.g momentum params) could be tuned like beta1 and beta2 and decay

    if optimizer == 'RMSProp': 
        optimizer_configured = keras.optimizers.RMSprop(learning_rate=learning_rate, decay=learning_rate / 100)

    elif optimizer == 'SGD': 
        optimizer_configured = keras.optimizers.SGD(learning_rate=learning_rate / 10, decay=learning_rate / 100)

    elif optimizer == 'AdaGrad':
        optimizer_configured = keras.optimizers.Adagrad(learning_rate=learning_rate, decay=learning_rate / 100)
    
    elif optimizer == 'Nadam': 
        optimizer_configured = keras.optimizers.Nadam(learning_rate=learning_rate)
    
    else: 
        optimizer_configured = keras.optimizers.Adam(learning_rate=learning_rate, decay=learning_rate / 100)

    return optimizer_configured


def get_static_hparams(args): 
    '''Creates dict of static params for logging

    Arguments: 
        args: Parsed input params
    
    returns Dict with static params for logging purpose
    '''
    logging_ret = dict()
    LOGGING_ARGS = [
                    'schedule_step',
                    'batch_size',
                    'filter_hour_above',
                    'filter_category_noisy',
                    ]

    for key in LOGGING_ARGS:
        if vars(args)[key] is not None: 
            logging_ret[key] = vars(args)[key]

    logging_ret['date'] = int(datetime.now().strftime("%m%d%H"))

    if (args.warm_start_path is not None) and (args.warm_start_path is not 'None'): 
        logging_ret['warm_start'] = True
    else: 
        logging_ret['warm_start'] = False

    return logging_ret


def create_callbacks(logdir, hparams=None, save_best=True, reduce_on_plateau=False, max_metrics=None, schedule_step=0): 
    '''Creates keras callbacks for training

    Arguments: 
        logdir: Path to directory where shall be logged
        hparams: Sample of hyperparameters for this run
        save_best: Flag if best model during training shall be saved
        reduce_on_plateau: Flag if callback for reducing the learning rate at
                           detected plateau shall be included
    '''

    if logdir == None: 
        return None

    callbacks = list()
    tensorboard_callback = keras.callbacks.TensorBoard(
            log_dir                = logdir,
            update_freq            = 128, 
            profile_batch          = 0, 
            write_graph            = False,
            write_grads            = True, 
            histogram_freq         = 128,
        )
        
    callbacks.append(tensorboard_callback)
    callbacks.append(hp.KerasCallback(logdir, hparams))

    if save_best: 
        save_path = os.path.join(logdir, '{epoch:02d}_{val_loss:.2f}.hdf5')
        callbacks.append(keras.callbacks.ModelCheckpoint(save_path,
                                                          monitor='val_acc_rescaled',
                                                          save_best_only=True, 
                                                          mode='max', 
                                                          verbose=1))

    if reduce_on_plateau: 
        callbacks.append(keras.callbacks.ReduceLROnPlateau(
            monitor    = 'val_loss',
            factor     = 0.05,
            patience   = 4,
            verbose    = 1,
            mode       = 'auto',
            min_delta  = 0.001,
            cooldown   = 0,
            min_lr     = 1e-8
        ))
    
    if hparams['schedule_step'] > 0:

        def lr_scheduler(epoch, lr):
            """ Schedule the learning rate
            """
            decay_rate = 0.5

            if epoch % hparams['schedule_step'] == 0 and epoch:
                return lr * decay_rate
            else: 
                return lr

        callbacks.append(keras.callbacks.LearningRateScheduler(lr_scheduler, verbose=1))

    for name, mode in max_metrics.items(): 
        callbacks.append(Evaluate(name, mode, logdir))

    callbacks.append(keras.callbacks.EarlyStopping(monitor='val_acc_rescaled', min_delta=0.1, patience=20, verbose=0, mode='max'))

    return callbacks




