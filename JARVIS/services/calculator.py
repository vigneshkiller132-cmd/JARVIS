import ast
import math
import operator
import re
import config

def _safe_eval(expr):
    _ops = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg,
        ast.UAdd: operator.pos, ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }
    _fns = {name: getattr(math, name) for name in dir(math) if not name.startswith('_')}

    def _eval(node):
        if isinstance(node, ast.Expression): return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
        if isinstance(node, ast.BinOp):
            op = _ops.get(type(node.op))
            if op is None: raise ValueError("Unsupported operator")
            return op(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op = _ops.get(type(node.op))
            if op is None: raise ValueError("Unsupported operator")
            return op(_eval(node.operand))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _fns:
                args = [_eval(a) for a in node.args]
                return _fns[node.func.id](*args)
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    tree = ast.parse(expr, mode='eval')
    return _eval(tree)

def calculate(text):
    expr = re.sub(r'\b(what is|calculate|compute|solve|how much is|equals?)\b', '', text, flags=re.I)
    expr = expr.replace('x', '*').replace('times', '*').replace('divided by', '/') \
               .replace('plus', '+').replace('minus', '-').replace('power', '**') \
               .replace('squared', '**2').replace('cubed', '**3')
    expr = re.sub(r'[^0-9+\-*/.() a-zA-Z_]', '', expr).strip()
    if not expr: return None
    try:
        result = _safe_eval(expr)
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return f"{expr} equals {result} {config.YOUR_NAME}."
    except Exception:
        return None

def unit_convert(text):
    conversions = {
        ('km', 'miles'): 0.621371, ('miles', 'km'): 1.60934,
        ('kg', 'pounds'): 2.20462, ('pounds', 'kg'): 0.453592,
        ('meters', 'feet'): 3.28084, ('feet', 'meters'): 0.3048,
        ('celsius', 'fahrenheit'): None, ('fahrenheit', 'celsius'): None,
        ('liters', 'gallons'): 0.264172, ('gallons', 'liters'): 3.78541,
        ('inches', 'cm'): 2.54, ('cm', 'inches'): 0.393701,
    }
    m = re.search(r'(\d+\.?\d*)\s*(\w+)\s+(?:to|in|into)\s+(\w+)', text)
    if not m: return None
    val, from_u, to_u = float(m.group(1)), m.group(2).lower(), m.group(3).lower()
    key = (from_u, to_u)
    if key == ('celsius', 'fahrenheit'):
        r = val*9/5+32; return f"{val} Celsius is {r:.2f} Fahrenheit {config.YOUR_NAME}."
    if key == ('fahrenheit', 'celsius'):
        r = (val-32)*5/9; return f"{val} Fahrenheit is {r:.2f} Celsius {config.YOUR_NAME}."
    if key in conversions:
        r = val * conversions[key]; return f"{val} {from_u} is {r:.4f} {to_u} {config.YOUR_NAME}."
    return None