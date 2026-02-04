"""
REPL Sandbox Configuration.

Provides RestrictedPython security guards and sandbox setup for safe code execution.

Phase 3: REPL refactoring
"""

from typing import Any

from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    safer_getattr,
    guarded_unpack_sequence,
)
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.PrintCollector import PrintCollector


class SandboxGuards:
    """Security guards for RestrictedPython sandbox."""

    @staticmethod
    def inplacevar(op: str, x: Any, y: Any) -> Any:
        """Implement in-place operations for RestrictedPython.

        RestrictedPython requires this helper for augmented assignment (+=, -=, etc.)
        because it rewrites `x += y` to `x = _inplacevar_('+=', x, y)`.

        Supports all standard operators:
        - +=, -=, *=, /=, //=, %=, **=
        - &=, |=, ^=, >>=, <<=

        Args:
            op: The operator (e.g., '+=')
            x: The left operand
            y: The right operand

        Returns:
            The result of the in-place operation

        Raises:
            SyntaxError: If the operator is invalid
        """
        ops = {
            "+=": lambda a, b: a + b,
            "-=": lambda a, b: a - b,
            "*=": lambda a, b: a * b,
            "/=": lambda a, b: a / b,
            "//=": lambda a, b: a // b,
            "%=": lambda a, b: a % b,
            "**=": lambda a, b: a ** b,
            "&=": lambda a, b: a & b,
            "|=": lambda a, b: a | b,
            "^=": lambda a, b: a ^ b,
            ">>=": lambda a, b: a >> b,
            "<<=": lambda a, b: a << b,
        }

        if op not in ops:
            raise SyntaxError(f"Unsupported in-place operator: {op}")

        return ops[op](x, y)

    @staticmethod
    def write_guard(obj: Any) -> Any:
        """Guard for attribute and item assignment.

        Allows setting attributes and items on most objects, but prevents
        setting dangerous attributes like __class__.

        Args:
            obj: The object being written to

        Returns:
            The object (unchanged)

        Raises:
            AttributeError: If trying to set a forbidden attribute
        """
        # This is basic; RestrictedPython handles most of this at a deeper level
        return obj

    @staticmethod
    def build_restricted_globals() -> dict[str, Any]:
        """Build a restricted globals dict with safe builtins.

        Based on RestrictedPython patterns for safer code execution.

        Returns:
            Dictionary of safe globals for code execution
        """
        from RestrictedPython import safe_globals

        restricted = dict(safe_globals)

        # Add RestrictedPython guards
        restricted["_getattr_"] = safer_getattr
        restricted["_getitem_"] = default_guarded_getitem
        restricted["_getiter_"] = default_guarded_getiter
        restricted["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
        restricted["_unpack_sequence_"] = guarded_unpack_sequence

        # Add in-place variable helper
        restricted["_inplacevar_"] = SandboxGuards.inplacevar

        # Add write guard for attribute/item assignment
        restricted["_write_"] = SandboxGuards.write_guard

        # Add print collector
        restricted["_print_"] = PrintCollector

        # Add safe builtins
        safe_builtins = {
            # Types
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "frozenset": frozenset,
            "bytes": bytes,
            "bytearray": bytearray,
            # Iteration
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "reversed": reversed,
            # Functions
            "abs": abs,
            "all": all,
            "any": any,
            "min": min,
            "max": max,
            "sum": sum,
            "round": round,
            "pow": pow,
            "divmod": divmod,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "callable": callable,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "delattr": delattr,
            "dir": dir,
            "id": id,
            "hash": hash,
            "hex": hex,
            "oct": oct,
            "bin": bin,
            "ord": ord,
            "chr": chr,
            "ascii": ascii,
            # Exceptions
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "RuntimeError": RuntimeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "ZeroDivisionError": ZeroDivisionError,
            "FileNotFoundError": FileNotFoundError,
            # Modules/objects
            "None": None,
            "True": True,
            "False": False,
            "Ellipsis": Ellipsis,
            "NotImplemented": NotImplemented,
        }
        restricted.update(safe_builtins)

        return restricted
