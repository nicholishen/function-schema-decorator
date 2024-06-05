"""
Purpose: Contains the validate_schema function to validate the generated schema.
Functions:
validate_schema: Validates the structure of a JSON schema.
"""

from typing import Any, Dict


def validate_schema(schema: Dict[str, Any]) -> bool:
    # Check top-level keys
    required_top_keys = {"type", "function"}
    if not required_top_keys.issubset(schema.keys()):
        print("Missing top-level keys")
        return False

    # Check 'function' structure
    function = schema["function"]
    required_function_keys = {"name", "description", "parameters"}
    if not required_function_keys.issubset(function.keys()):
        print("Missing function keys")
        return False

    parameters = function["parameters"]
    if parameters["type"] != "object":
        print("Invalid parameters type")
        return False
    if "properties" not in parameters or not isinstance(parameters["properties"], dict):
        print("Invalid properties")
        return False
    if "required" not in parameters or not isinstance(parameters["required"], list):
        return False

    def check_properties(properties: Dict[str, Any]) -> bool:
        for prop, details in properties.items():
            if "oneOf" in details:
                for option in details["oneOf"]:
                    if not ("type" in option and "description" in details):
                        print(f"Invalid oneOf option in property: {prop}")
                        return False
            else:
                if "type" not in details or "description" not in details:
                    print(f"Invalid property: {prop}, missing 'type' or 'description'")
                    return False
                if details["type"] == "object":
                    if "properties" not in details or not isinstance(
                        details["properties"], dict
                    ):
                        print(f"Invalid nested properties in: {prop}")
                        return False
                    if not check_properties(details["properties"]):
                        return False
                elif details["type"] == "array":
                    if "items" not in details or not isinstance(details["items"], dict):
                        print(f"Invalid items in array: {prop}")
                        return False
                    # Special case for validating items
                    item_details = details["items"]
                    if not ("type" in item_details and "description" in details):
                        print(
                            f"Invalid item in array: {prop}, missing 'type' or 'description'"
                        )
                        return False
        return True

    # Check all properties recursively
    if not check_properties(parameters["properties"]):
        return False

    return True
