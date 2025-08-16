from google import genai
from google.genai import types
import re
import json
import requests
from typing import Dict, Any, Optional
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

def create_gemini_chat(client, tools: list):
    return client.chats.create(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            tools=tools,
            system_instruction=system_instruction,
        )
    )

def init_vertex_client(project_id: str = None, location: str = None, corpus_id: str = None):
    """Initialize the Vertex AI client with the provided project ID location, and corpus ID"""
    if not project_id :
        project_id = os.getenv("PROJECT_ID")
    if not location:
        location = os.getenv("LOCATION")
    if not corpus_id:
        corpus_id = os.getenv("CORPUS_ID")
    if not (project_id and location and corpus_id) :
        raise ValueError("Please provide a valid project ID, location, and corpus ID.")

    client = genai.Client(
        project=project_id,
        location=location,
        vertexai=True,
    )
    rag_tool = types.Tool(
        retrieval=types.Retrieval(
            vertex_rag_store=types.VertexRagStore(
                rag_resources=[
                    types.VertexRagStoreRagResource(
                        rag_corpus=f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
                    )
                ]
            )
        )
    )
    return client, rag_tool

def init_genai_client(api_key: str = None):
    """Initialize the Gemini API client with the provided API key"""
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("No API key provided. Please provide a Gemini API key.")
    
    return genai.Client(api_key=api_key)

def create_chat_session(rag: bool, api_key: str = None, project_id: str = None, location: str = None, corpus_id: str = None):
    """Create a new chat session with the provided API key"""

    # We can only use RAG or Google Search
    if rag:
        client, rag_tool = init_vertex_client(project_id, location, corpus_id)
        return create_gemini_chat(client, [rag_tool])
    else:
        client = init_genai_client(api_key)
        return create_gemini_chat(client, [types.Tool(google_search=types.GoogleSearch())])

date = date.today()

json_converter = """
You are a JSON converter bot. Your goal is to take text and output to a JSON object with the following columns:
email
customer_initial_question
business_use_case
budget
timeline_in_months
is_qualified
"""

system_instruction = f"""
You are Formlabs Sales Representative, Rhys, and your goal is to answer questions from customers and determine if they are actually interested in buying a Formlabs printer in the next 60 days.

You should use information primarily sourced from formlabs.com and support.formlabs.com to answer questions. But you can also use general information from the web if you cannot find an answer on these websites. For price related questions, use https://formlabs.com/store/

You are communicating in a chat platform and your answers should be concise, informative, and slightly more casual than email.

Once you answer the customer question  and any follow-up questions, you should ask them questions to understand their need for 3d printers. You should only ask one question at a time to understand the customer's needs. You should only ask up to two questions on need or application. Once you are able to give a suggestion to the customer, do not ask more questions on customers’ needs. 

When you suggest a 3D printer option, for SLA you should first offer either Form 4, Form 4L or Form 4B depending on customers’ needs and for SLS, you should offer Fuse 1+. Don’t recommend form 4B if the customer wants a material which is not one of the biocompatible material resins. 

Once you have collected information, you should ask them what their general budget, timeline for purchase, and email address is. You should qualify anyone with a budget over $3000 (or local currency equivalent) and a timeline to purchase a printer in the next four months.

If the customer says they don’t have a budget or they are unsure of their budget, don’t force them but give them the best option formlabs has given whatever you were able to collect and then ask something along the lines of ‘is there anything else I can share to help with your purchase decision?’. If the customer says no to this, you can refer them to our webstore to buy the product you think is the best. 

 If the customer is not qualified, ask the customer to browse the store at https://formlabs.com/store.  If they don’t respond, politely end the conversation. If they respond and say they want to talk to an agent on the phone, ask them of their budget and when they’ll buy. You can frame it as something you need to direct them to the right team. 

If the customer is qualified, you can do one of 3 things:

If they need more tailored recommendation and/or if the option they are interested in is above $10,000 (or local currency equivalent) - Tell them a sales representative will reach out today if the request is within business hours: 9am -5pm Local time (local time of the customer's country), or the next business day if the request is outside business hours . 
If they are ready to buy now or as soon as possible and the option they are interested in is less than $10,000 (or local currency equivalent), refer them to the relevant webstore page to complete the purchase
If they are not qualified, you should ask them if they have any other questions or politely end the conversation.

If a qualified customer wants to talk to an agent, get their email and phone number and mention that a sales rep will contact them shortly. Don't keep asking for budget if they told you they don't really have a budget but are looking for the best or right solution

In general, use less words and don't repeat business hours.

Once you have all the information below, you should summarize this information to a JSON String name data.json with the following columns
The JSON formatted String should only have the JSON object, and no other characters:

email
customer_initial_question - STRING
overview_of_customers_business_and_use_case_for_3d_printing - STRING
budget - INT
estimated_purchase_date - DATE(YYYY-MM-DD Format), if given a date, return the date. If given a number of months, add it to {date} and return that
is_qualified (Yes or No) - STRING

"""

def is_json_response(response):
    try:
        # Attempt to parse the response text as JSON
        formatted_data = response.text.replace('```json', '').replace('```', '').strip()
        json_data = json.loads(formatted_data)
        return True
    except json.JSONDecodeError:
        # If json.loads() raises a JSONDecodeError, it's not valid JSON
        return False
    except AttributeError:
        # Handle cases where response.text might not be a string (e.g., None)
        return False

def query_llm(chat_session, question: str):
    """Send a message to the LLM and get the response"""
    try:
        response = chat_session.send_message(question)
        return response
    except Exception as e:
        raise Exception(f"Error querying LLM: {str(e)}")

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON objects from the response text.
    Looks for JSON patterns and attempts to parse them.
    """
    # Pattern to find JSON objects in the response
    json_pattern = r'```json\s*(\{.*?\})\s*```'
    json_matches = re.findall(json_pattern, response, re.DOTALL)

    if json_matches:
        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    return None


def create_opportunity(data):
    # Replace with your actual Zapier webhook URL
    zapier_webhook_url = 'https://hooks.zapier.com/hooks/catch/18996039/u41k77t/'

    # Data you want to send
    # payload = {
    #     "email": "mg@formlabs.com",
    #     "customer_initial_question": "i am the owner of an airsoft company who is making end user parts and want to buy a 3d printer",
    #     "overview_of_customers_business_and_use_case_for_3d_printing": "Owner of an airsoft company making end-user parts.",
    #     "budget": 10000,
    #     "estimated_purchase_date": "2025-10-01",
    #     "is_qualified": "Yes"
    # }

    # # Convert the dict to a JSON-formatted string
    payload_json = json.dumps(data)

    # Set headers to indicate you're sending JSON
    headers = {'Content-Type': 'application/json'}

    # Send POST request with JSON payload
    response = requests.post(zapier_webhook_url, data=payload_json, headers=headers)

    # Print the response
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")


# Create initial chat session
chat = create_chat_session(rag=True)