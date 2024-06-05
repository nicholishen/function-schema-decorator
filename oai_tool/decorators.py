"""
Purpose: Provides decorators and functions to generate function schemas and decorate functions with schema metadata.
Functions:
get_function_schema: Generates a schema for a given function.
tool: Decorator to add schema metadata to a function.
reorder_keys: Reorders keys in a dictionary to ensure 'description' is first.
process_schema: Recursively reorders keys in a schema.
"""

import inspect
import logging
from typing import Any, Callable, Dict, Optional

from .schema_generation import (
    get_default_values,
    get_param_annotations,
    get_parameters,
    get_required_params,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_function_schema(
    f: Callable[..., Any],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    typed_signature = inspect.signature(f)
    required = get_required_params(typed_signature)
    default_values = get_default_values(typed_signature)
    param_annotations = get_param_annotations(typed_signature)
    return_annotation = typed_signature.return_annotation

    if return_annotation is inspect.Signature.empty:
        logger.warning(
            f"The return type of the function '{f.__name__}' is not annotated. Although annotating it is "
            + "optional, the function should return either a string, a subclass of 'pydantic.BaseModel'."
        )

    fname = name if name else f.__name__
    fdescription = description if description else f.__doc__ or ""

    parameters = get_parameters(
        required, param_annotations, default_values=default_values
    )

    function_schema = {
        "type": "function",
        "function": {
            "name": fname,
            "description": fdescription,
            "parameters": parameters,
        },
    }

    # Add an indicator if the function is async
    if inspect.iscoroutinefunction(f):
        function_schema["function"]["async"] = True

    return function_schema


def tool(
    function: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
):
    def actual_decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        f._schema = get_function_schema(f, name=name, description=description)

        if inspect.iscoroutinefunction(f):

            async def async_wrapper(*args, **kwargs):
                return await f(*args, **kwargs)
            async_wrapper._schema = f._schema

            return async_wrapper
        else:
            return f

    if function:
        return actual_decorator(function)
    return actual_decorator


def reorder_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """Reorder keys to ensure 'description' is the first key."""
    new_d = {}
    if "description" in d:
        new_d["description"] = d["description"]
    for k, v in d.items():
        if k != "description":
            new_d[k] = v
    return new_d


def process_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively reorder keys in the schema."""
    if "properties" in schema:
        schema["properties"] = {
            k: process_schema(reorder_keys(v)) for k, v in schema["properties"].items()
        }
    if "items" in schema:
        schema["items"] = process_schema(reorder_keys(schema["items"]))
    return reorder_keys(schema)
