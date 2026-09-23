"""Local CAS fallback using sympy when available."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

def solve_expression(expr: str) -> Dict[str, Any]:
    expr = (expr or "").strip()
    if not expr:
        return {"ok": False, "error": "empty"}
    # strip $ and common latex noise lightly
    cleaned = expr.replace("$", "").replace("\\", "")
    cleaned = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1)/(\2)", expr.replace("$", ""))
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        transforms = standard_transformations + (implicit_multiplication_application,)
        if "=" in cleaned and cleaned.count("=") == 1:
            left, right = cleaned.split("=", 1)
            e = sp.Eq(parse_expr(left, transformations=transforms), parse_expr(right, transformations=transforms))
            syms = list(e.free_symbols)
            if not syms:
                return {"ok": True, "input": expr, "result": str(e), "mode": "relation"}
            sols = sp.solve(e, syms)
            return {"ok": True, "input": expr, "result": str(sols), "mode": "solve"}
        e = parse_expr(cleaned, transformations=transforms)
        simplified = sp.simplify(e)
        numeric = None
        try:
            numeric = float(simplified.evalf())
        except Exception:
            pass
        return {
            "ok": True,
            "input": expr,
            "simplified": str(simplified),
            "result": str(simplified),
            "numeric": numeric,
            "mode": "simplify",
        }
    except ImportError:
        return {"ok": False, "error": "sympy not installed", "input": expr}
    except Exception as e:
        return {"ok": False, "error": str(e), "input": expr}
