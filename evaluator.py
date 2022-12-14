# Standard imports
import torch as tc
from time import time

# Project imports
from primitives import primitives
from utils import log_sample

# Parameters
run_name = 'start'

class Env(dict):
    'An environment: a dict of {var: val} pairs, with an outer environment'
    def __init__(self, parms=(), args=(), outer=None):
        self.update(zip(parms, args))
        self.outer = outer
    def find(self, var):
        'Find the innermost Env where var appears'
        if var in self:
            result = self
        else:
            if self.outer is None:
                # print('Not found in any environment:', var)
                raise ValueError('Outer limit of environment reached')
            else:
                result = self.outer.find(var)
        return result


class Procedure(object):
    'A user-defined HOPPL procedure'
    def __init__(self, params:list, body:list, sig:dict, env:Env):
        self.params, self.body, self.sig, self.env = params, body, sig, env
    def __call__(self, *args):
        return eval(self.body, self.sig, Env(self.params, args, self.env))


def standard_env():
    'An environment with some standard procedures'
    env = Env()
    env.update(primitives)
    return env


def eval(e, sig:dict, env:Env, verbose=False):

    if isinstance(e, bool):
        t = tc.tensor(e).float()
        return t
    
    elif isinstance(e, int) or isinstance(e, float):
        return tc.tensor(e).float()

    elif tc.is_tensor(e):
        return e

    elif isinstance(e, str):
        try:
            return env.find(e)[e]

        except:
            return e

    op, *args = e


    if op == "if":
        (test, conseq, alt) = args
        if eval(test, sig, env):
            exp = conseq
        else:
            exp = alt

        return eval(exp, sig, env)

    elif op == "sample" or op == "sample*":
        val = eval(args[1], sig, env)
        return val.sample()

    elif op == "observe" or op == "observe*":
        d = eval(args[1], sig, env)
        v = eval(args[2], sig, env)
        logp = d.log_prob(v)
        sig["logW"]+= logp
        return logp


    elif op == "fn":
        (parms, body) = args
        return Procedure(parms, body, sig, env)

    
    else:
        proc = eval(e[0], sig, env)
        args = []
        for arg in e[1:]:
            args.append(eval(arg, sig, env))

        if isinstance(proc, str):
            raise Exception("{} is not a procedure".format(proc))

        return proc(*args)
        


def evaluate(ast:dict, verbose=False):
    '''
    Evaluate a HOPPL program as desugared by daphne
    Args:
        ast: abstract syntax tree
    Returns: The return value of the program
    '''
    sig = {'logW':0}; env = standard_env()
    exp = eval(ast, sig, env, verbose)(run_name) # NOTE: Must run as function with *any* argument
    return exp


def get_samples(ast:dict, num_samples:int, tmax=None, wandb_name=None, verbose=False):
    '''
    Generate a set of samples from the prior of a FOPPL program
    '''
    samples = []
    if (tmax is not None): max_time = time()+tmax
    for i in range(num_samples):
        sample = evaluate(ast, verbose)
        if wandb_name is not None: log_sample(sample, i, wandb_name=wandb_name)
        samples.append(sample)
        if (tmax is not None) and time() > max_time: break
    return samples
