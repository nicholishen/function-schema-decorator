import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, Tuple
from pydantic import BaseModel, create_model, Field, ValidationError
from pydantic.fields import FieldInfo
from typing_extensions import Annotated, Literal, get_args, get_origin
from enum import Enum

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


def validate_llm_response(response: Any, expected_schema: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Validates the LLM's response against the expected schema.
    Returns a tuple (is_valid, data) where `is_valid` is a boolean indicating if the response is valid,
    and `data` is either the validated data or an error message string.
    """
    try:
        response_model = create_model_from_schema(expected_schema)
        validated_response = response_model(**response)
        return True, validated_response.model_dump()  # Use model_dump to handle the response
    except ValidationError as e:
        return False, e.errors()  # Return detailed error messages for LLM feedback


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


def get_parameter_json_schema(
    k: str, v: Any, default_values: Dict[str, Any]
) -> Dict[str, Any]:
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


def extract_annotated_type(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


def extract_annotation_metadata(annotation: Any) -> Optional[FieldInfo]:
    if get_origin(annotation) is Annotated:
        metadata = get_args(annotation)[1:]
        for meta in metadata:
            if isinstance(meta, FieldInfo):
                return meta
    return None


def type2schema(annotation: Any) -> Dict[str, Any]:
    field_info = extract_annotation_metadata(annotation)
    base_type = extract_annotated_type(annotation)

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
            properties = {
                prop_name: {
                    **type2schema(field.annotation),
                    "description": field.description or prop_name,
                }
                for prop_name, field in base_type.model_fields.items()
            }
            model_description = base_type.__doc__ or getattr(
                base_type.model_config, "title", ""
            )
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
            if hasattr(meta, "ge"):
                schema["minimum"] = meta.ge
            if hasattr(meta, "lt"):
                schema["exclusiveMaximum"] = meta.lt
            if hasattr(meta, "le"):
                schema["maximum"] = meta.le

    return schema


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
