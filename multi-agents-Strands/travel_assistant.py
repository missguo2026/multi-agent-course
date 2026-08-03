import csv
import json
import os
from io import StringIO

import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool


app = BedrockAgentCoreApp()

S3_BUCKET = os.environ["S3_BUCKET"]

s3_client = boto3.client("s3")


def find_rows(s3_key, filters):
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)

    csv_text = response["Body"].read().decode("utf-8")

    rows = list(csv.DictReader(StringIO(csv_text)))

    matches = []

    for row in rows:
        if all(
            not value
            or row[column].strip().lower() == value.strip().lower()
            for column, value in filters.items()
        ):
            matches.append(row)

    return json.dumps(matches, indent=2)


@tool
def search_restaurants(city: str, fine_dining: str = "") -> str:
    """Find restaurants in the course database.

    Args:
        city: City to search in.
        fine_dining: Optional preference. Use "Yes" or "No".

    Returns:
        Restaurants that match the requested city and fine-dining preference.
    """
    return find_rows(
        "restaurant.csv",
        {"City": city, "Fine Dining": fine_dining},
    )


@tool
def search_hotels(location: str) -> str:
    """Find hotels in the course database.

    Args:
        location: City to search in.

    Returns:
        Hotels that match the requested location.
    """
    return find_rows("hotel.csv", {"Location": location})


@tool
def search_airbnbs(
    location: str,
    pets: str = "",
    pool: str = "",
    sauna: str = "",
) -> str:
    """Find Airbnbs in the course database.

    Args:
        location: City to search in.
        pets: Optional pet-friendly preference. Use "Yes" or "No".
        pool: Optional pool preference. Use "Yes" or "No".
        sauna: Optional sauna preference. Use "Yes" or "No".

    Returns:
        Airbnbs that match the requested location and preferences.
    """
    return find_rows(
        "airbnb.csv",
        {
            "Location": location,
            "Pets": pets,
            "Pool": pool,
            "Sauna": sauna,
        },
    )


restaurant_agent = Agent(
    name="restaurant_agent",
    description="Finds restaurants by city and fine-dining preference.",
    system_prompt="""
You are the restaurant specialist.
Use search_restaurants for every restaurant request.
Only recommend restaurants returned by the tool.
If there are no matches, say that the database has no matching restaurant.
""",
    tools=[search_restaurants],
)


accommodation_agent = Agent(
    name="accommodation_agent",
    description="Finds hotels and Airbnbs by location and accommodation preferences.",
    system_prompt="""
You are the accommodation specialist.
Use search_hotels for hotel requests and search_airbnbs for Airbnb requests.
If the user asks for both, call both tools.
Only recommend accommodations returned by the tools.
If there are no matches, say that the database has no matching accommodation.
""",
    tools=[search_hotels, search_airbnbs],
)


supervisor_agent = Agent(
    name="travel_supervisor",
    system_prompt="""
You are a travel supervisor coordinating specialist agents.

- Use restaurant_agent for restaurant and dining requests.
- Use accommodation_agent for hotel and Airbnb requests.
- If a request needs both dining and accommodation, call both specialists.
- Combine their results into one concise answer.
- Never invent a listing that a specialist did not return.
""",
    tools=[restaurant_agent, accommodation_agent],
)


@app.entrypoint
def invoke(payload):
    user_request = payload.get("prompt", "")

    if not isinstance(user_request, str) or not user_request.strip():
        return {"response": "Please provide a non-empty prompt."}

    result = supervisor_agent(user_request.strip())

    return {"response": str(result)}


if __name__ == "__main__":
    app.run()
