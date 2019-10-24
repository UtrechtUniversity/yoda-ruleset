# -*- coding: utf-8 -*-
# \brief     Experimental Python/Rule interface code.
# \author    Chris Smeele
# \copyright Copyright (c) 2019 Utrecht University. All rights reserved.
# \license   GPLv3, see LICENSE.

# This file is currently named iiA.py so that it is the first file in the concatenation train.
# ideally we would drop this requirement by switching to a module-based approach.

from enum import Enum
import json


class RuleOutput(Enum):
    """Specifies rule output handlers."""
    STORE  = 0  # store in output parameters
    STDOUT = 1  # write to stdout


def rule(inputs=None, outputs=None, transform=lambda x: x, handler=RuleOutput.STORE):
    """Turns a python function into a rule.
       (intended to be used as a decorator)

       The benefit comes from being able to use a function both as a normal
       python function (with python calling conventions), and as a rule.

       Decorator arguments:

       inputs and outputs can optionally be specified as lists of indices to
       influence how parameters are passed to this function, and how the return
       value is processed. By default, 'inputs' and 'outputs' both span all rule arguments.

       transform can be used to apply a transformation to the returned value(s),
       e.g. by encoding them as JSON.

       handler specifies what to do with the (transformed) return value(s):
       - RuleOutput.STORE:  stores return value(s) in output parameter(s) (this is the default)
       - RuleOutput.STDOUT: prints return value(s) to stdout

       Examples:

           @rule(inputs=[0,1], outputs=[2])
           def foo(callback, x, y):
               return int(x) + int(y)

       is equivalent to:

           def foo(rule_args, callback, rei):
               x, y = rule_args[0:2]
               rule_args[2] = int(x) + int(y)

       and...

           @rule(transform=json.dumps, handler=RuleOutput.STDOUT)
           def foo(callback, x, y):
               return {'result': int(x) + int(y)}

       is equivalent to:

           def foo(rule_args, callback, rei):
               x, y = rule_args[0:2]
               callback.writeString('stdout', json.dumps(int(x) + int(y)))
    """
    def deco(f):
        def r(rule_args, callback, rei):
            result = f(callback, *rule_args if inputs is None else [rule_args[i] for i in inputs])

            if result is None:
                return

            result = map(transform, list(result) if type(result) is tuple else [result])

            if handler is RuleOutput.STORE:
                if outputs is None:
                    # outputs not specified? overwrite all arguments.
                    rule_args[:] = map(str, result)
                else:
                    # set specific output arguments.
                    for i, x in zip(outputs, result):
                        rule_args[i] = str(x)
            elif handler is RuleOutput.STDOUT:
                for x in result:
                    callback.writeString('stdout', str(x))
                    # XXX for debugging:
                    # callback.writeString('serverLog', 'rule output (DEBUG): ' + str(x))
        return r
    return deco


def define_as_rule(name, **options):
    """Registers a rule with the provided name as a wrapper for the given function.
       This does not change the behavior of the function itself.
       This way, a function can be both used from python and called from rules.

       note: the rule name and the function name must not be the same.

       Example:

       @define_as_rule('fooRule', inputs=[0,1], outputs=[2])
       def foo(callback, x, y):
           return int(x) + int(y)

       now running `foo(callback, 40, 2)` from python will yield 42 as expected,
       and `*x = ''; fooRule('40', '2', *x)` will result in *x being set to 42.
    """
    def deco(f):
        globals()[name] = rule(**options)(f)
        return f
    return deco
