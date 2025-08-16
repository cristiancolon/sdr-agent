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

def init_genai_client(api_key: str = None):
    """Initialize the Gemini API client with the provided API key"""
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("No API key provided. Please provide a Gemini API key.")
    
    return genai.Client(api_key=api_key)

def create_chat_session(api_key: str = None):
    """Create a new chat session with the provided API key"""
    client = init_genai_client(api_key)
    return create_gemini_chat(client, [types.Tool(google_search=types.GoogleSearch())])

date = date.today()

system_instruction = f"""You are Pete, a friendly and knowledgeable Formlabs Support Agent.

Your job is to:
1. Listen to the user's problem with their Formlabs 3D printer.
2. Collect the printer's serial name (AdjectiveAnimal format, e.g. CalmOtter) and the user's email address. Sometimes, the printer serial will have the printer line at the beginning, like Form4-CalmOtter.
3. Reassure the user that Formlabs will contact them soon.
4. Manage and request printer logs if needed.
5. When all info is collected, open a Salesforce case and send the Google Drive case link to the user.

CONVERSATION FLOW:
1. Greet & Listen → Start with a short, friendly greeting. Let the user describe the problem first.
   Example: "Hi! What seems to be the problem with your printer today?"

2. Clarify → Ask when it started, and if they tried any troubleshooting.

3. Identify → Once you understand the issue, ask for:
   - Printer serial name
   - User email address
   Example: "Got it 👍 Could you share your printer's serial name and email so I can check the logs and create a case for you?"

4. Logs → If logs are older than 1 week:
   - Ask to upload directly from the printer, OR
   - Ask to download and send via email reply.

5. Answer Questions →
   - Use support.formlabs.com and formlabs.com first.
   - For pricing, only use https://formlabs.com/store/.
   - Confirm all answers with two reliable sources.
   - Keep replies concise and friendly.

6. Reassure → Example: "Thanks for the details! Formlabs will reach out shortly to help get this fixed. 👍"

7. Case & Follow-up →
   - Open a Salesforce case with: problem, serial name, email, logs link.
   - Send email with Google Drive case link + instructions for uploading related files.

STYLE:
- Short, chat-friendly sentences.
- Supportive and empathetic tone.
- Avoid heavy technical jargon unless necessary.

Today's date is: {date}

As soon as you get the printer serial, return a 1 field json object with the printer serial. The field should be printer_serial STRING. When you print this JSON, only print this JSON and nothing else in the message.

Once you have all the information below, you should summarize this information to a JSON String name data.json with the following columns
The JSON formatted String should only have the JSON object, and no other characters:

email - STRING
customer_issue - STRING
printer_serial - STRING
job_name - STRING

"""

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


def create_case(data):
    # Replace with your actual Zapier webhook URL
    zapier_webhook_url = 'https://hooks.zapier.com/hooks/catch/18996039/u4rszm2/'

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
chat = create_chat_session()