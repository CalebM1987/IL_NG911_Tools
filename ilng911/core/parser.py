import re
import ast
import math
import operator
from .fields import FIELDS
from ..support.munch import munchify


STREET_DIRECTIONS_ABBR = munchify(dict(
    NORTH='N',
    NORTHEAST='NE',
    NORTHWEST='NW',
    SOUTH='S',
    SOUTHEAST='SE',
    SOUTHWEST='SW',
    EAST='E',
    WEST='W',
))

class CUSTOM_TOKENS:
    PreDirectionAbbr = 'PreDirectionAbbr'
    PostDirectionAbbr = 'PostDirectionAbbr'
    StreetTypeAbbr = 'StreetTypeAbbr'

def get_string_tokens(s: str):
    return re.findall(r"(\{.*?\})", s)

 
def safe_eval(s):
    """safely evaluate an expression, particularly for mathematic expressions

    https://stackoverflow.com/a/68732605
    
    Args:
        s (_type_): the string to evaluate
    """

    def checkmath(x, *args):
        if x not in [x for x in dir(math) if not "__" in x]:
            raise SyntaxError(f"Unknown func {x}()")
        fun = getattr(math, x)
        return fun(*args)

    binOps = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Call: checkmath,
        ast.BinOp: ast.BinOp,
    }

    unOps = {
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.UnaryOp: ast.UnaryOp,
    }

    ops = tuple(binOps) + tuple(unOps)

    tree = ast.parse(s, mode='eval')

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Num):
            return node.value
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            if isinstance(node.left, ops):
                left = _eval(node.left)
            else:
                left = node.left.value
            if isinstance(node.right, ops):
                right = _eval(node.right)
            else:
                right = node.right.value
            return binOps[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.operand, ops):
                operand = _eval(node.operand)
            else:
                operand = node.operand.value
            return unOps[type(node.op)](operand)
        elif isinstance(node, ast.Call):
            args = [_eval(x) for x in node.args]
            r = checkmath(node.func.id, *args)
            return r
        else:
            raise SyntaxError(f"Bad syntax, {type(node)}")

    return _eval(tree)


    

