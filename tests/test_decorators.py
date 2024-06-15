# import asyncio
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union

import pytest
from pydantic import BaseModel, Field

from oai_tool import tool, validate_schema
from oai_tool.decorators import process_schema
import asyncio


def test_string():
    @tool
    def test_string(value: Annotated[str, Field(description="A string value")]) -> str:
        """A string value"""
        return value

    schema = test_string.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_string"
    assert schema["function"]["description"] == "A string value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "string"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A string value"
    )


def test_number():
    @tool(name="test_number", description="A number value")
    def test_number(
        value: Annotated[float, Field(description="A number value")]
    ) -> float:
        return value

    schema = test_number.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_number"
    assert schema["function"]["description"] == "A number value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "number"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A number value"
    )


def test_integer():
    @tool
    def test_integer(
        value: Annotated[int, Field(description="An integer value")]
    ) -> int:
        """An integer value"""
        return value

    schema = test_integer.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_integer"
    assert schema["function"]["description"] == "An integer value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "An integer value"
    )


def test_boolean():
    @tool(name="test_boolean", description="A boolean value")
    def test_boolean(
        value: Annotated[bool, Field(description="A boolean value")]
    ) -> bool:
        return value

    schema = test_boolean.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_boolean"
    assert schema["function"]["description"] == "A boolean value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "boolean"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A boolean value"
    )


def test_array():
    @tool
    def test_array(
        value: Annotated[List[str], Field(description="An array of strings")]
    ) -> List[str]:
        """An array of strings"""
        return value

    schema = test_array.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_array"
    assert schema["function"]["description"] == "An array of strings"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "array"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["items"]["type"]
        == "string"
    )
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "An array of strings"
    )


class NestedModel(BaseModel):
    nested_value: str = Field(description="A nested value")


def test_object():
    @tool
    def test_object(
        value: Annotated[NestedModel, Field(description="An object value")]
    ) -> NestedModel:
        """An object value"""
        return value

    schema = test_object.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_object"
    assert schema["function"]["description"] == "An object value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "object"
    assert (
        "nested_value"
        in schema["function"]["parameters"]["properties"]["value"]["properties"]
    )


class Color(Enum):
    red = "red"
    green = "green"
    blue = "blue"


def test_enum():
    @tool
    def test_enum(value: Annotated[Color, Field(description="An enum value")]) -> Color:
        """An enum value"""
        return value

    schema = test_enum.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_enum"
    assert schema["function"]["description"] == "An enum value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "string"
    assert schema["function"]["parameters"]["properties"]["value"]["enum"] == [
        "red",
        "green",
        "blue",
    ]
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "An enum value"
    )


def test_const():
    @tool(name="test_const", description="A constant value")
    def test_const(
        value: Annotated[
            Literal["constant_value"], Field(description="A constant value")
        ]
    ) -> str:
        return value

    schema = test_const.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "test_const"
    assert schema["function"]["description"] == "A constant value"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "string"
    assert schema["function"]["parameters"]["properties"]["value"]["enum"] == [
        "constant_value"
    ]
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A constant value"
    )


class Address(BaseModel):
    street: Annotated[str, Field(description="The street address")]
    city: Annotated[str, Field(description="The city")]
    zip_code: Annotated[str, Field(description="The ZIP code")]


class User(BaseModel):
    name: Annotated[str, Field(description="The name of the user")]
    age: Annotated[int, Field(description="The age of the user")]
    address: Annotated[Address, Field(description="The address of the user")]
    friends: Annotated[List[Address], Field(description="A list of friend's addresses")]


def test_create_user():
    @tool
    def create_user(
        user: Annotated[User, Field(description="The user object to create")]
    ) -> str:
        """Creates a new user"""
        return f"User {user.name} created"

    schema = create_user.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "create_user"
    assert schema["function"]["description"] == "Creates a new user"
    assert "user" in schema["function"]["parameters"]["properties"]
    user_props = schema["function"]["parameters"]["properties"]["user"]["properties"]
    assert user_props["name"]["type"] == "string"
    assert user_props["name"]["description"] == "The name of the user"
    assert user_props["age"]["type"] == "integer"
    assert user_props["age"]["description"] == "The age of the user"
    assert user_props["address"]["type"] == "object"
    assert user_props["address"]["description"] == "The address of the user"
    assert "street" in user_props["address"]["properties"]
    assert "friends" in user_props
    assert user_props["friends"]["type"] == "array"
    assert user_props["friends"]["items"]["type"] == "object"


def test_list_of_objects():
    class SimpleObject(BaseModel):
        property_one: str = Field(description="The first property")
        property_two: str = Field(description="The second property")

    @tool
    def process_objects(
        objects: Annotated[List[SimpleObject], Field(description="A list of objects")]
    ) -> str:
        """Processes a list of objects"""
        return f"Processed {len(objects)} objects"

    schema = process_objects.schema
    reordered_schema = process_schema(schema)

    assert validate_schema(reordered_schema)
    assert reordered_schema["function"]["name"] == "process_objects"
    assert reordered_schema["function"]["description"] == "Processes a list of objects"
    assert (
        reordered_schema["function"]["parameters"]["properties"]["objects"]["type"]
        == "array"
    )
    assert (
        reordered_schema["function"]["parameters"]["properties"]["objects"]["items"][
            "type"
        ]
        == "object"
    )
    assert (
        reordered_schema["function"]["parameters"]["properties"]["objects"][
            "description"
        ]
        == "A list of objects"
    )
    object_props = reordered_schema["function"]["parameters"]["properties"]["objects"][
        "items"
    ]["properties"]
    assert object_props["property_one"]["type"] == "string"
    assert object_props["property_one"]["description"] == "The first property"
    assert object_props["property_two"]["type"] == "string"
    assert object_props["property_two"]["description"] == "The second property"


def test_complex_literals():
    @tool
    def complex_literals(
        value: Annotated[
            Literal["option1", "option2"], Field(description="A literal value")
        ]
    ) -> str:
        """Function with complex literals"""
        return value

    schema = complex_literals.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "complex_literals"
    assert schema["function"]["description"] == "Function with complex literals"
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "string"
    assert schema["function"]["parameters"]["properties"]["value"]["enum"] == [
        "option1",
        "option2",
    ]
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A literal value"
    )


def test_no_parameters():
    @tool
    def no_params() -> str:
        """Function with no parameters"""
        return "No parameters"

    schema = no_params.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "no_params"
    assert schema["function"]["description"] == "Function with no parameters"
    assert (
        schema["function"]["parameters"]["properties"] == {}
    )  # Check for empty properties
    assert (
        schema["function"]["parameters"]["required"] == []
    )  # Check for empty required list


def test_union_types():
    @tool
    def union_types(
        value: Annotated[Union[int, str], Field(description="An int or str value")]
    ) -> str:
        """Function with union types"""
        return str(value)

    schema = union_types.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "union_types"
    assert schema["function"]["description"] == "Function with union types"

    # Union types might be represented using "oneOf" in the schema
    assert "oneOf" in schema["function"]["parameters"]["properties"]["value"]
    types = schema["function"]["parameters"]["properties"]["value"]["oneOf"]
    type_strings = [type_schema["type"] for type_schema in types]
    assert "string" in type_strings
    assert "integer" in type_strings


def test_optional_parameters():
    @tool
    def optional_params(
        required_value: Annotated[str, Field(description="A required value")],
        optional_value: Annotated[
            Optional[str], Field(description="An optional value")
        ] = None,
    ) -> str:
        """Function with optional parameters"""
        return required_value + (optional_value or "")

    schema = optional_params.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "optional_params"
    assert schema["function"]["description"] == "Function with optional parameters"
    assert (
        schema["function"]["parameters"]["properties"]["required_value"]["type"]
        == "string"
    )
    assert (
        schema["function"]["parameters"]["properties"]["required_value"]["description"]
        == "A required value"
    )
    assert (
        schema["function"]["parameters"]["properties"]["optional_value"]["type"]
        == "string"
    )
    assert (
        schema["function"]["parameters"]["properties"]["optional_value"]["description"]
        == "An optional value"
    )


def test_empty_strings_and_lists():
    @tool
    def handle_empty(
        empty_string: Annotated[str, Field(description="An empty string")],
        empty_list: Annotated[List[str], Field(description="An empty list")],
    ) -> str:
        """Handles empty strings and lists"""
        return f"String: {empty_string}, List: {empty_list}"

    schema = handle_empty.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "handle_empty"
    assert schema["function"]["description"] == "Handles empty strings and lists"
    assert (
        schema["function"]["parameters"]["properties"]["empty_string"]["type"]
        == "string"
    )
    assert (
        schema["function"]["parameters"]["properties"]["empty_string"]["description"]
        == "An empty string"
    )
    assert (
        schema["function"]["parameters"]["properties"]["empty_list"]["type"] == "array"
    )
    assert (
        schema["function"]["parameters"]["properties"]["empty_list"]["items"]["type"]
        == "string"
    )
    assert (
        schema["function"]["parameters"]["properties"]["empty_list"]["description"]
        == "An empty list"
    )


def test_positive_number():
    @tool
    def positive_number(
        value: Annotated[int, Field(description="A positive number", gt=0)]
    ) -> str:
        """Function with a number that must be greater than 0"""
        return f"The number is {value}"

    schema = positive_number.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "positive_number"
    assert (
        schema["function"]["description"]
        == "Function with a number that must be greater than 0"
    )
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A positive number"
    )
    assert (
        schema["function"]["parameters"]["properties"]["value"]["exclusiveMinimum"] == 0
    )


def test_rank_feedback():
    @tool
    def rank_feedback(
        value: Annotated[
            int,
            Field(
                description="Rank the customer's feedback on a scale of 1 to 10",
                ge=1,
                le=10,
            ),
        ]
    ) -> str:
        """Function to rank customer's feedback on a scale of 1 to 10"""
        return f"The feedback rank is {value}"

    schema = rank_feedback.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "rank_feedback"
    assert (
        schema["function"]["description"]
        == "Function to rank customer's feedback on a scale of 1 to 10"
    )
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "Rank the customer's feedback on a scale of 1 to 10"
    )
    assert schema["function"]["parameters"]["properties"]["value"]["minimum"] == 1
    assert schema["function"]["parameters"]["properties"]["value"]["maximum"] == 10


def test_process_temperature():
    @tool
    def process_temperature(
        temperature: Annotated[
            float,
            Field(
                description="Temperature in Celsius (must be between -273.15 and 1000.0)",
                ge=-273.15,
                le=1000.0,
            ),
        ]
    ) -> str:
        """Function to process temperature in Celsius"""
        return f"The temperature is {temperature}°C"

    schema = process_temperature.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "process_temperature"
    assert (
        schema["function"]["description"]
        == "Function to process temperature in Celsius"
    )
    assert (
        schema["function"]["parameters"]["properties"]["temperature"]["type"]
        == "number"
    )
    assert (
        schema["function"]["parameters"]["properties"]["temperature"]["description"]
        == "Temperature in Celsius (must be between -273.15 and 1000.0)"
    )
    assert (
        schema["function"]["parameters"]["properties"]["temperature"]["minimum"]
        == -273.15
    )
    assert (
        schema["function"]["parameters"]["properties"]["temperature"]["maximum"]
        == 1000.0
    )


def test_enum_in_field():
    class TemperatureUnit(Enum):
        CELSIUS = "celsius"
        FAHRENHEIT = "fahrenheit"

    @tool
    def get_current_weather(
        location: Annotated[
            str, Field(description="The city and state, e.g. San Francisco, CA")
        ],
        format: Annotated[
            TemperatureUnit,
            Field(
                description="The temperature unit to use. Infer this from the user's location."
            ),
        ],
    ) -> dict:
        """Get the current weather"""
        return {
            "location": location,
            "temperature": "25°C" if format == TemperatureUnit.CELSIUS else "77°F",
            "condition": "Sunny",
        }

    schema = get_current_weather.schema
    print("Schema for get_current_weather:", schema)
    assert validate_schema(schema)
    assert schema["function"]["name"] == "get_current_weather"
    assert schema["function"]["description"] == "Get the current weather"
    properties = schema["function"]["parameters"]["properties"]
    assert properties["location"]["type"] == "string"
    assert (
        properties["location"]["description"]
        == "The city and state, e.g. San Francisco, CA"
    )
    assert properties["format"]["type"] == "string"
    assert properties["format"]["enum"] == ["celsius", "fahrenheit"]
    assert (
        properties["format"]["description"]
        == "The temperature unit to use. Infer this from the user's location."
    )


def test_async_function():
    @tool
    async def async_func(
        value: Annotated[str, Field(description="A string value")]
    ) -> str:
        """An async function that returns the string value"""
        await asyncio.sleep(0.1)  # Simulate async operation
        return value

    schema = async_func.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "async_func"
    assert (
        schema["function"]["description"]
        == "An async function that returns the string value"
    )
    assert schema["function"]["parameters"]["properties"]["value"]["type"] == "string"
    assert (
        schema["function"]["parameters"]["properties"]["value"]["description"]
        == "A string value"
    )
    assert schema["function"]["async"]

    # Testing the actual function
    result = asyncio.run(async_func("test"))
    assert result == "test"


def test_regular_function():
    @tool
    def add_numbers(
        a: Annotated[int, Field(description="The first number")],
        b: Annotated[int, Field(description="The second number")],
    ) -> int:
        """Adds two integers and returns the sum."""
        return a + b

    schema = add_numbers.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "add_numbers"
    assert schema["function"]["description"] == "Adds two integers and returns the sum."
    assert schema["function"]["parameters"]["properties"]["a"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["a"]["description"]
        == "The first number"
    )
    assert schema["function"]["parameters"]["properties"]["b"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["b"]["description"]
        == "The second number"
    )

    result = add_numbers(3, 4)
    assert result == 7


class Calculator:
    @tool
    def add(
        self,
        a: Annotated[int, Field(description="The first number")],
        b: Annotated[int, Field(description="The second number")],
    ) -> int:
        """Adds two integers and returns the sum."""
        return a + b


def test_class_method():
    calc = Calculator()
    schema = calc.add.schema
    assert validate_schema(schema)
    assert schema["function"]["name"] == "add"
    assert schema["function"]["description"] == "Adds two integers and returns the sum."
    assert schema["function"]["parameters"]["properties"]["a"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["a"]["description"]
        == "The first number"
    )
    assert schema["function"]["parameters"]["properties"]["b"]["type"] == "integer"
    assert (
        schema["function"]["parameters"]["properties"]["b"]["description"]
        == "The second number"
    )

    result = calc.add(3, 4)
    assert result == 7


if __name__ == "__main__":
    pytest.main()
