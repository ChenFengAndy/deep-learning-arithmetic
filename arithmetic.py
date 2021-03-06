# Copyright 2014 Matthieu Courbariaux

# This file is part of Deep learning arithmetic simulator.

# Deep learning arithmetic simulator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Deep learning arithmetic simulator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Deep learning arithmetic simulator.  If not, see <http://www.gnu.org/licenses/>.

import gzip
import cPickle
import numpy as np
import os
import os.path
import sys
import theano 
import theano.tensor as T
import time

from theano.scalar.basic import UnaryScalarOp, same_out_nocomplex
from theano.tensor.elemwise import Elemwise

def simulate_format(format, X, NOB, NOIB):
    
    if format == "FXP" or format == "DFXP": 
        return fixed_point(X,NOB, NOIB)
        
    elif format == "FLP":
        return X
        
    elif format == "HFLP":
        return float16(X)     

# float16 function
# we are using the nvidia cuda function (only works on GPU)
class Float16(UnaryScalarOp):

    def impl(self, x):
        return numpy.float32(numpy.float16(x))
    
    def c_code(self, node, name, (x,), (z,), sub):
        return "%(z)s = __half2float(__float2half_rn(%(x)s));" % locals()  
float16_scalar = Float16(same_out_nocomplex, name='float16')
float16 = Elemwise(float16_scalar)
        
# this function simulate the precision and the range of a fixed point 
# while working with floats
# NOB = Number Of Bits = bit-width
# NOIB = Number Of Integer Bits = position of the radix point = range
def fixed_point(X,NOB, NOIB):
    
    power = T.cast(2.**(NOB - NOIB), theano.config.floatX) # float !
    max = T.cast((2.**NOB)-1, theano.config.floatX)
    value = X*power    
    value = T.round(value) # rounding
    value = T.clip(value, -max, max) # saturation arithmetic
    value = value/power
    return value
        
# compute the new range of the dynamic fixed point representation
def new_range(overflow, overflow_1, max_overflow):
    
    # the goal is to update the range of the vector 
    # we know the overflow rates associated with range (overflow) 
    # and range-1 (overflow_1)
    # if (overflow > max_overflow): increment range
    # else if (overflow_1 < max_overflow): decrement range
    return T.switch(T.gt(overflow, max_overflow), 1, 
        T.switch(T.gt(overflow_1, max_overflow), 0, - 1))

# Overflow rate of a vector knowing its NOIB and NOB
def overflow(vector, NOB, NOIB):
    
    # compute the max value of the fixed point representation (i.e. the overflow value)
    max = ((2.**NOB)-1)/(2.**(NOB - NOIB))
    
    # compute the overflow rate of the vector
    overflow = T.mean(T.switch(T.ge(T.abs_(vector), max), 1., 0.))
    
    return overflow
    