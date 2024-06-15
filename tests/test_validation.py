import pytest
from pydantic import BaseModel, Field
from typing import Annotated, List, Optional
from oai_tool import tool, validate_schema
from oai_tool.decorators import Tool


def test_advanced_validation():
    class Address(BaseModel):
        street: Annotated[str, Field(description="The street address", min_length=1)]
        city: Annotated[str, Field(description="The city", min_length=1)]
        zip_code: Annotated[str, Field(description="The ZIP code", pattern=r'^\d{5}$')]

    class User(BaseModel):
        name: Annotated[str, Field(description="The name of the user", min_length=1)]
        age: Annotated[int, Field(description="The age of the user", ge=0)]
        address: Annotated[Address, Field(description="The address of the user")]
        friends: Annotated[Optional[List[Address]], Field(description="A list of friends' addresses", default=None)]

    @tool
    def create_user(user: Annotated[User, Field(description="The user object to create")]) -> str:
        """Creates a new user"""
        return f"User {user.name} created"

    schema = create_user.schema
    assert validate_schema(schema)

    # Valid response
    valid_response = {
        "user": {
            "name": "John Doe",
            "age": 30,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "zip_code": "12345"
            },
            "friends": [
                {
                    "street": "456 Elm St",
                    "city": "Othertown",
                    "zip_code": "67890"
                }
            ]
        }
    }
    valid_result = create_user.validate_response(valid_response, schema)
    assert valid_result == True

    # Invalid response: missing required field
    invalid_response_missing_field = {
        "user": {
            "age": 30,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "zip_code": "12345"
            },
            "friends": [
                {
                    "street": "456 Elm St",
                    "city": "Othertown",
                    "zip_code": "67890"
                }
            ]
        }
    }
    invalid_result_missing_field = create_user.validate_response(invalid_response_missing_field, schema)
    print("Validation result for missing field:", invalid_result_missing_field)
    assert isinstance(invalid_result_missing_field, str)  # Should return error message as a string

    # Invalid response: incorrect field type
    invalid_response_incorrect_type = {
        "user": {
            "name": "John Doe",
            "age": "thirty",  # Should be an integer
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "zip_code": "12345"
            },
            "friends": [
                {
                    "street": "456 Elm St",
                    "city": "Othertown",
                    "zip_code": "67890"
                }
            ]
        }
    }
    invalid_result_incorrect_type = create_user.validate_response(invalid_response_incorrect_type, schema)
    print("Validation result for incorrect type:", invalid_result_incorrect_type)
    assert isinstance(invalid_result_incorrect_type, str)  # Should return error message as a string

    # Invalid response: pattern constraint violation
    invalid_response_pattern_violation = {
        "user": {
            "name": "John Doe",
            "age": 30,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "zip_code": "ABCDE"  # Should be a 5-digit number
            },
            "friends": [
                {
                    "street": "456 Elm St",
                    "city": "Othertown",
                    "zip_code": "67890"
                }
            ]
        }
    }
    invalid_result_pattern_violation = create_user.validate_response(invalid_response_pattern_violation, schema)
    print("Validation result for pattern violation:", invalid_result_pattern_violation)
    assert isinstance(invalid_result_pattern_violation, str)  # Should return error message as a string
