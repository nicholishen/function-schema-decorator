"""
Purpose: Contains functions to generate JSON schemas from Python type annotations.
Functions:
extract_annotated_type: Extracts the main type from an Annotated type.
extract_annotation_metadata: Extracts metadata from Annotated.
type2schema: Converts a Python type to a JSON schema type.
get_parameter_json_schema: Generates a JSON schema for a parameter.
get_required_params: Retrieves required parameters from a function signature.
get_default_values: Retrieves default values from a function signature.
get_param_annotations: Retrieves parameter annotations from a function signature.
get_parameters: Constructs the parameters schema.
"""

import inspect
from typing import Any, Dict, List, Type, Union, Optional
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Annotated, Literal, get_args, get_origin
from enum import Enum

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_annotated_type(annotation: Any) -> Any:
    """Extract the main type from an Annotated type."""
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


def extract_annotation_metadata(annotation: Any) -> Optional[FieldInfo]:
    """Extract the metadata from Annotated."""
    origin = get_origin(annotation)
    if origin is FieldInfo:
        return annotation
    if get_origin(annotation) is Annotated:
        metadata = get_args(annotation)[1:]
        for meta in metadata:
            if isinstance(meta, FieldInfo):
                logger.debug(f"Extracted metadata: {meta}")
                return meta
    return None


def type2schema(annotation: Any) -> Dict[str, Any]:
    field_info = extract_annotation_metadata(annotation)
    base_type = extract_annotated_type(annotation)

    print(f"Processing type: {base_type}, with metadata: {field_info}")

    schema = {}

    if get_origin(base_type) is Literal:
        schema = {"type": "string", "enum": list(get_args(base_type))}
    elif isinstance(base_type, type):
        if issubclass(base_type, bool):
            schema = {"type": "boolean"}
        elif issubclass(base_type, str):
            schema = {"type": "string"}
        elif issubclass(base_type, int) and not issubclass(base_type, bool):
            schema = {"type": "integer"}
        elif issubclass(base_type, float):
            schema = {"type": "number"}
        elif issubclass(base_type, BaseModel):
            properties = {}
            fields_items = base_type.model_fields.items()
            for prop_name, field in fields_items:
                properties[prop_name] = {
                    **type2schema(field),
                    "description": field.field_info.description or prop_name,
                }
            # properties = {
            #     prop_name: {
            #         **type2schema(field.annotation),
            #         "description": field.field_info.description or prop_name,
            #     }
            #     for prop_name, field in base_type.__fields__.items()
            # }
            model_description = base_type.__doc__ or getattr(base_type.Config, "title", "")
            schema = {
                "type": "object",
                "properties": properties,
                "description": model_description,
            }
        elif issubclass(base_type, Enum):
            schema = {"type": "string", "enum": [e.value for e in base_type]}
    elif get_origin(base_type) is list:
        schema = {"type": "array", "items": type2schema(get_args(base_type)[0])}
    elif get_origin(base_type) is Union:
        args = get_args(base_type)
        if len(args) == 2 and type(None) in args:
            non_none_type = args[0] if args[1] is type(None) else args[1]
            schema = type2schema(non_none_type)
            schema["nullable"] = True
        else:
            schema = {"oneOf": [type2schema(arg) for arg in args]}
    else:
        raise TypeError(f"Unsupported type: {base_type}")

    if field_info and field_info.metadata:
        for meta in field_info.metadata:
            if hasattr(meta, "gt"):
                schema["exclusiveMinimum"] = meta.gt
                print(f"Applied exclusiveMinimum constraint: {meta.gt}")
            if hasattr(meta, "ge"):
                schema["minimum"] = meta.ge
                print(f"Applied minimum constraint: {meta.ge}")
            if hasattr(meta, "lt"):
                schema["exclusiveMaximum"] = meta.lt
                print(f"Applied exclusiveMaximum constraint: {meta.lt}")
            if hasattr(meta, "le"):
                schema["maximum"] = meta.le
                print(f"Applied maximum constraint: {meta.le}")

    print(f"Generated schema: {schema}")
    return schema



def get_parameter_json_schema(
    k: str, v: Any, default_values: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate JSON schema for a parameter."""
    schema = type2schema(v)
    if k in default_values:
        dv = default_values[k]
        schema["default"] = dv

    metadata = extract_annotation_metadata(v)
    if metadata and metadata.description:
        schema["description"] = metadata.description
    else:
        schema["description"] = k

    return schema


def get_required_params(typed_signature: inspect.Signature) -> List[str]:
    return [
        k
        for k, v in typed_signature.parameters.items()
        if v.default == inspect.Signature.empty
    ]


def get_default_values(typed_signature: inspect.Signature) -> Dict[str, Any]:
    return {
        k: v.default
        for k, v in typed_signature.parameters.items()
        if v.default != inspect.Signature.empty
    }


def get_param_annotations(
    typed_signature: inspect.Signature,
) -> Dict[str, Union[Annotated[Type[Any], str], Type[Any]]]:
    return {
        k: v.annotation
        for k, v in typed_signature.parameters.items()
        if v.annotation is not inspect.Signature.empty
    }


def get_parameters(
    required: List[str],
    param_annotations: Dict[str, Union[Annotated[Type[Any], str], Type[Any]]],
    default_values: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            k: get_parameter_json_schema(k, v, default_values)
            for k, v in param_annotations.items()
            if v is not inspect.Signature.empty
        },
        "required": required,
    }


if __name__ == "__main__":

    from pydantic import Field

    test_annotation = Annotated[int, Field(description="The person's age, must be non-negative", ge=0)]
    schema = type2schema(test_annotation)    
    print(schema)
    # # Define a simple Pydantic model
    # from pydantic import BaseModel, Field
    # from typing import Annotated

    # class Person(BaseModel):
    #     name: str = Field(description="The person's name")
    #     age: Annotated[
    #         int, Field(ge=0, description="The person's age, must be non-negative")
    #     ]

    # annotation = getattr(Person, "__annotations__")["age"]
    # metadata = extract_annotation_metadata(annotation)
    # base_type = extract_annotated_type(annotation)

    # # Use pdb to step through the type2schema function
    # import pdb

    # # pdb.set_trace()
    # type2schema(annotation)
