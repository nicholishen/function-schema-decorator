import pytest
from pydantic import BaseModel, Field
from typing import List, Annotated
from llm_codebridge.core import generate_function_schema, validate_llm_response
from llm_codebridge.validation import validate_schema
import json

# def test_list_of_people():
#     class Person(BaseModel):
#         name: Annotated[str, Field(description="The name of the person")]
#         age: Annotated[int, Field(description="The age of the person", ge=0)]

#     def process_people(people: Annotated[List[Person], Field(description="A list of people")]) -> str:
#         """Processes a list of people"""
#         return f"Processed {len(people)} people"

#     schema = generate_function_schema(process_people)
#     print(json.dumps(schema, indent=2))
#     assert validate_schema(schema)

#     # Valid response
#     valid_response = {
#         "people": [
#             {"name": "Alice", "age": 30},
#             {"name": "Bob", "age": 25}
#         ]
#     }
#     is_valid, result = validate_llm_response(valid_response, schema)
#     assert is_valid
#     assert result["people"][0]["name"] == "Alice"
#     assert result["people"][0]["age"] == 30
#     assert result["people"][1]["name"] == "Bob"
#     assert result["people"][1]["age"] == 25

#     # Invalid response: age is negative
#     invalid_response_negative_age = {
#         "people": [
#             {"name": "Alice", "age": -30},
#             {"name": "Bob", "age": 25}
#         ]
#     }
#     is_valid, result = validate_llm_response(invalid_response_negative_age, schema)
#     assert not is_valid  # Check for invalidity correctly
#     assert 'age' in result[0]['loc']  # Ensure the error message points to 'age'


# Define the Person model
class Person(BaseModel):
    name: str = Field(description="The name of the person")
    age: int = Field(ge=0, description="The age of the person, must be non-negative")

# Define the function to be tested
def process_person(person: Annotated[Person, Field(description="A person object")]) -> str:
    """Processes a single person"""
    return f"Processed person named {person.name} aged {person.age}"

# Define the test for this function
def test_process_person():
    # Generate schema
    schema = generate_function_schema(process_person)
    print("Generated Schema:\n", json.dumps(schema, indent=2))

    # Valid response
    valid_person = {"name": "John", "age": 30}
    is_valid, result = validate_llm_response(valid_person, schema)
    assert is_valid, f"Valid response failed: {result}"
    assert result['name'] == "John"
    assert result['age'] == 30

    # Invalid response: negative age
    invalid_person = {"name": "John", "age": -1}
    is_valid, result = validate_llm_response(invalid_person, schema)
    assert not is_valid, "Validation should fail for negative age"
    assert 'age' in result[0]['loc'], "Error location should be 'age'"

def test_validate_response():
    def validate_response_func(value: Annotated[str, Field(description="A string value")]) -> dict:
        """Function to test response validation"""
        return {"value": value}

    schema = generate_function_schema(validate_response_func)
    assert validate_schema(schema)

    # Valid response
    valid_response = {"value": "test"}
    is_valid, valid_result = validate_llm_response(valid_response, schema)
    assert is_valid
    assert isinstance(valid_result, dict)  # now checking the correct part of the tuple
    assert valid_result['value'] == "test"