import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, Tuple
from pydantic import BaseModel, create_model, Field, ValidationError
from pydantic.fields import FieldInfo
from typing_extensions import Annotated, Literal, get_args, get_origin
from enum import Enum
try:
    from schema_generation import (
        extract_annotated_type,
        extract_annotation_metadata,
        type2schema,
        get_required_params,
        get_default_values,
        get_param_annotations,
        get_parameters,
    )
except ImportError:
    from .schema_generation import (
        extract_annotated_type,
        extract_annotation_metadata,
        type2schema,
        get_required_params,
        get_default_values,
        get_param_annotations,
        get_parameters,
    )

TYPE_MAPPING = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def generate_function_schema(
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
        return_annotation = None

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
        "name": fname,
        "description": fdescription,
        "parameters": parameters,
    }

    # Add an indicator if the function is async
    if inspect.iscoroutinefunction(f):
        function_schema["async"] = True

    return {
        "type": "function",  # Ensure top-level type key
        "function": function_schema,
    }


def parse_type(type_info: Dict[str, Any]) -> Any:
    if "oneOf" in type_info:
        return Union[tuple(parse_type(option) for option in type_info["oneOf"])]
    return TYPE_MAPPING.get(type_info["type"], Any)


def create_model_from_schema(schema: Dict[str, Any]) -> BaseModel:
    function_schema = schema["function"]
    parameters_schema = function_schema["parameters"]

    fields = {}
    required_fields = parameters_schema.get("required", [])
    for key, value in parameters_schema["properties"].items():
        field_type = TYPE_MAPPING[value["type"]]
        default = ... if key in required_fields else None
        fields[key] = (
            field_type,
            Field(default=default, description=value.get("description", "")),
        )

    return create_model(function_schema["name"] + "Model", **fields)


def validate_llm_response(
    response: Any, expected_schema: Dict[str, Any]
) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Validates the LLM's response against the expected schema.
    Returns a tuple (is_valid, data) where `is_valid` is a boolean indicating if the response is valid,
    and `data` is either the validated data or an error message string.
    """
    try:
        response_model = create_model_from_schema(expected_schema)
        validated_response = response_model(**response)
        return (
            True,
            validated_response.model_dump(),
        )  # Use model_dump to handle the response
    except ValidationError as e:
        return False, e.errors()  # Return detailed error messages for LLM feedback


def process_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    def reorder_keys(d: Dict[str, Any]) -> Dict[str, Any]:
        new_d = {}
        if "description" in d:
            new_d["description"] = d["description"]
        for k, v in d.items():
            if k != "description":
                new_d[k] = v
        return new_d

    def recursive_reorder(d: Dict[str, Any]) -> Dict[str, Any]:
        if "properties" in d:
            d["properties"] = {
                k: recursive_reorder(reorder_keys(v))
                for k, v in d["properties"].items()
            }
        if "items" in d:
            d["items"] = recursive_reorder(reorder_keys(d["items"]))
        return reorder_keys(d)

    return recursive_reorder(schema)


if __name__ == '__main__':
    # Define a simple Pydantic model
    from pydantic import BaseModel, Field
    from typing import Annotated

    class Person(BaseModel):
        name: Annotated[str, Field(description="The name of the person")]
        age: Annotated[int, Field(ge=0, description="The age of the person, must be non-negative")]

    # Define the function to be tested
    def process_person(person: Annotated[Person, Field(description="The person of interest.")]) -> str:
        """Processes a single person"""
        return f"Processed person named {person.name} aged {person.age}"

    # Generate schema
    schema = generate_function_schema(process_person)
   