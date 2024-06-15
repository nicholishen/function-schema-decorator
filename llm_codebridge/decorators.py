"""
Purpose: Provides decorators and functions to generate function schemas and decorate functions with schema metadata.
Functions:
get_function_schema: Generates a schema for a given function.
reorder_keys: Reorders keys in a dictionary to ensure 'description' is first.
process_schema: Recursively reorders keys in a schema.
"""

import inspect
import logging
from typing import Any, Callable, Dict, Optional, Union
from pydantic import BaseModel, create_model, ValidationError, Field

from .schema_generation import (
    get_default_values,
    get_param_annotations,
    get_parameters,
    get_required_params,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TYPE_MAPPING = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def get_function_schema(
    f: Callable[..., Any],
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_method: bool = False,
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

    if is_method:
        # Remove 'self' or 'cls' from parameters
        param_annotations.pop("self", None)
        param_annotations.pop("cls", None)
        required = [r for r in required if r not in ("self", "cls")]
        default_values.pop("self", None)
        default_values.pop("cls", None)

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


def create_pydantic_model_from_schema(schema: Dict[str, Any]) -> BaseModel:
    """
    Dynamically creates a Pydantic model based on the provided schema.
    """

    def parse_type(type_info: Dict[str, Any]) -> Any:
        if "oneOf" in type_info:
            return Union[tuple(parse_type(option) for option in type_info["oneOf"])]
        return TYPE_MAPPING.get(type_info["type"], Any)

    fields = {}
    required_fields = schema["function"]["parameters"].get("required", [])
    for key, value in schema["function"]["parameters"]["properties"].items():
        field_type = parse_type(value)
        default = ... if key in required_fields else None
        fields[key] = (
            field_type,
            Field(default=default, description=value.get("description", "")),
        )

    return create_model(schema["function"]["name"] + "Model", **fields)


class Tool:
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        self.name = name
        self.description = description
        self.schema = None

    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        is_method = (
            "self" in inspect.signature(f).parameters
            or "cls" in inspect.signature(f).parameters
        )
        f.schema = get_function_schema(
            f, name=self.name, description=self.description, is_method=is_method
        )
        input_model = create_pydantic_model_from_schema(f.schema)
        self.input_model = input_model

        if inspect.iscoroutinefunction(f):

            async def async_wrapper(*args, **kwargs):
                bound_args = inspect.signature(f).bind(*args, **kwargs)
                bound_args.apply_defaults()
                try:
                    validated_data = {
                        k: v for k, v in bound_args.arguments.items() if k != "self"
                    }
                    self.input_model(**validated_data)
                except ValidationError as e:
                    logger.error(f"Validation error: {e}")
                    raise e
                result = await f(*args, **bound_args.kwargs)
                return result

            async_wrapper.schema = f.schema
            async_wrapper.validate_response = self.validate_response
            return async_wrapper
        else:

            def wrapper(*args, **kwargs):
                bound_args = inspect.signature(f).bind(*args, **kwargs)
                bound_args.apply_defaults()
                try:
                    validated_data = {
                        k: v for k, v in bound_args.arguments.items() if k != "self"
                    }
                    self.input_model(**validated_data)
                except ValidationError as e:
                    logger.error(f"Validation error: {e}")
                    raise e
                result = f(*args, **bound_args.kwargs)
                return result

            wrapper.schema = f.schema
            wrapper.validate_response = self.validate_response
            return wrapper

    def validate_response(
        self, response: Any, expected_schema: Dict[str, Any]
    ) -> Union[bool, str]:
        """
        Validates the response against the expected schema and provides feedback if validation fails.
        This function will return True if validation is successful, or a string describing the validation errors if it fails.
        """
        logger.info(
            f"Validating response: {response} against schema: {expected_schema}"
        )
        try:
            response_model = create_pydantic_model_from_schema(expected_schema)
            response_model.model_validate(
                response
            )  # Use model_validate to ensure proper error handling
            return True
        except ValidationError as e:
            error_message = e.errors()
            logger.error(f"Response validation error: {error_message}")
            return str(
                error_message
            )  # Convert the error message to a string to satisfy the test's expectation


# Wrapper function to maintain compatibility with the previous `tool` decorator
def tool(
    function: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
):
    decorator = Tool(name=name, description=description)

    if function:
        return decorator(function)

    return decorator


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
