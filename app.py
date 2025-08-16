import streamlit as st
import sys
import os
from sales_backend.chat import create_chat_session as create_sales_chat, query_llm as query_sales_llm, extract_json_from_response as sales_extract_json_from_response, create_opportunity
from services_backend.chat import create_chat_session as create_services_chat, query_llm as query_services_llm, extract_json_from_response as services_extract_json_from_response, create_case
from services_backend.bigquery import run_recent_jobs_query
from dotenv import load_dotenv
from datetime import datetime
import hashlib

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Rhys by Formlabs",
    layout="wide"
)

# Generate a consistent random avatar based on session
def get_user_avatar():
    """Generate a consistent user avatar URL using DiceBear Personas style"""
    # Use session state to ensure same avatar per session, or generate new one
    if "user_avatar_seed" not in st.session_state:
        # Create a unique seed for this session
        import time
        import random
        seed = f"user_{int(time.time())}_{random.randint(1000, 9999)}"
        st.session_state.user_avatar_seed = seed
    
    # Use DiceBear Personas API with the session seed
    avatar_url = f"https://api.dicebear.com/9.x/personas/svg?seed={st.session_state.user_avatar_seed}&size=64&backgroundColor=f0f0f0"
    return avatar_url 

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if "is_typing" not in st.session_state:
    st.session_state.is_typing = False
if "use_rag" not in st.session_state:
    st.session_state.use_rag = True
if "project_id" not in st.session_state:
    st.session_state.project_id = os.getenv("PROJECT_ID", "")
if "location" not in st.session_state:
    st.session_state.location = os.getenv("LOCATION", "")
if "corpus_id" not in st.session_state:
    st.session_state.corpus_id = os.getenv("CORPUS_ID", "")
if "chatbot_type" not in st.session_state:
    st.session_state.chatbot_type = "sales"

# Add styles
st.markdown(
    """
    <style>
        /* Basic styling */
        .main {
            background-color: white;
            color: #2C353D;
        }

        /* Header styling */
        .chat-header {
            background-color: white;
            padding: 1.5rem 0;
            display: flex;
            align-items: center;
            gap: 1rem;
            border-bottom: 1px solid #E5E9ED;
        }
        
        .chat-header img {
            height: 32px;
            width: auto;
        }
        
        .chat-header h1 {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-left: auto;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            background-color: #00C853;
            border-radius: 50%;
            display: inline-block;
            margin-right: 4px;
        }

        .status-text {
            color: #4A5561;
            font-size: 0.875rem;
        }

        /* Timestamp */
        .message-timestamp {
            font-size: 0.75rem;
            color: #4A5561;
            margin-top: 0.25rem;
        }

        /* Typing animation */
        @keyframes typing {
            0% { content: ''; }
            25% { content: '.'; }
            50% { content: '..'; }
            75% { content: '...'; }
        }
        
        .typing-animation {
            color: #4A5561;
            font-size: 1rem;
            display: inline-block;
        }
        
        .typing-animation::after {
            content: '';
            display: inline-block;
            animation: typing 1.5s infinite;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# Header with properly aligned status
chatbot_name = "Rhys" if st.session_state.chatbot_type == "sales" else "Pete"

st.markdown(
    f"""
    <div class="chat-header">
        <img src="https://media.licdn.com/dms/image/v2/D4D0BAQFqNX1MQczSxw/company-logo_200_200/company-logo_200_200/0/1730299217728/formlabs_logo?e=1756944000&v=beta&t=zxowo3-TuCKBp5ad1JwOb4hOFc57bvB5MaTo1GuRvv0" alt="Formlabs Logo">
        <h1>{chatbot_name} by Formlabs</h1>
        <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">Online</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar with settings
with st.sidebar:
    st.title("Settings")
    
    # Chatbot Type Selection
    chatbot_type = st.selectbox(
        "Chatbot Type",
        options=["sales", "services"],
        index=0 if st.session_state.chatbot_type == "sales" else 1,
        format_func=lambda x: "Sales - Rhys" if x == "sales" else "Services - Pete",
        help="Choose between Sales (Rhys) or Services (Pete) chatbot"
    )
    
    # Check if chatbot type changed
    if chatbot_type != st.session_state.chatbot_type:
        st.session_state.chatbot_type = chatbot_type
        # Clear chat session to force recreation
        if "chat_session" in st.session_state:
            del st.session_state.chat_session
        # Clear messages when switching modes
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # Only show RAG toggle for sales chatbot
    if st.session_state.chatbot_type == "sales":
        # RAG Toggle
        use_rag = st.toggle("Use RAG (Vertex AI)", value=st.session_state.use_rag, 
                           help="Toggle between RAG (Vertex AI) and Google Search")
    else:
        # Services chatbot always uses Google Search
        use_rag = False
        st.session_state.use_rag = False
    
    # Check if RAG setting changed
    if use_rag != st.session_state.use_rag:
        st.session_state.use_rag = use_rag
        # Clear chat session to force recreation
        if "chat_session" in st.session_state:
            del st.session_state.chat_session
        # Clear messages when switching modes
        st.session_state.messages = []
        st.rerun()
    
    # API Key input (always visible)
    st.markdown("**Gemini API Settings:**")
    api_key = st.text_input("API Key", value=st.session_state.api_key, type="password", 
                           help="Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)")
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key
        if "chat_session" in st.session_state:
            del st.session_state.chat_session

    if use_rag:
        st.markdown("**RAG Settings (Vertex AI):**")
        # Project ID input
        project_id = st.text_input("Project ID", value=st.session_state.project_id, type="password",
                                  help="Google Cloud Project ID")
        if project_id != st.session_state.project_id:
            st.session_state.project_id = project_id
            if "chat_session" in st.session_state:
                del st.session_state.chat_session
        
        # Location input
        location = st.text_input("Location", value=st.session_state.location, type="password",
                                help="Google Cloud Location (e.g., us-central1)")
        if location != st.session_state.location:
            st.session_state.location = location
            if "chat_session" in st.session_state:
                del st.session_state.chat_session
        
        # Corpus ID input
        corpus_id = st.text_input("Corpus ID", value=st.session_state.corpus_id, type="password",
                                 help="RAG Corpus ID")
        if corpus_id != st.session_state.corpus_id:
            st.session_state.corpus_id = corpus_id
            if "chat_session" in st.session_state:
                del st.session_state.chat_session
    else:
        st.markdown("**Google Search Settings:**")
    
    # Clear chat button
    if st.button("Clear Chat", type="primary"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("**Instructions:**")
    
    if st.session_state.chatbot_type == "services":
        if not st.session_state.api_key:
            st.markdown("""
            **Services Mode (Pete):**
            1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
            2. Enter the API key above
            3. Start helping users with their 3D printer issues!
            """)
        else:
            st.markdown("""
            **Services Mode Active** ✅
            - Using Pete - Formlabs Services Agent
            - Ready to help with printer issues
            - Collects serial numbers and creates service cases
            """)
    elif use_rag:
        if not (st.session_state.project_id and st.session_state.location and st.session_state.corpus_id):
            st.markdown("""
            **RAG Mode (Vertex AI):**
            1. Enter your Google Cloud Project ID
            2. Enter the Location (e.g., us-central1)
            3. Enter your RAG Corpus ID
            4. Start chatting with RAG-enhanced responses!
            """)
        else:
            st.markdown("""
            **RAG Mode Active** ✅
            - Using Vertex AI with RAG
            - Enhanced with our proprietary knowledge corpus
            """)
    else:
        if not st.session_state.api_key:
            st.markdown("""
            **Google Search Mode:**
            1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
            2. Enter the API key above
            3. Start chatting with web search capabilities!
            """)
        else:
            st.markdown("""
            **Google Search Mode Active** ✅
            - Using Gemini with Google Search
            - Real-time web information
            """)

# Main chat interface
if not st.session_state.api_key:
    st.info("Please enter your Gemini API key in the settings")

if st.session_state.chatbot_type == "sales":
    if st.session_state.use_rag:
        st.caption("🤖 Sales Bot (Rhys) - RAG Mode - Enhanced with knowledge corpus")
    else:
        st.caption("🔍 Sales Bot (Rhys) - Google Search Mode - Real-time web search")
else:
    st.caption("🛠️ Services Bot (Pete) - Ready to help with your 3D printer issues")

# Chat interface
# Check if we have the required credentials
can_chat = False
if st.session_state.use_rag:
    can_chat = bool(st.session_state.project_id and st.session_state.location and st.session_state.corpus_id)
    if not can_chat:
        st.info("👈 Please enter your Vertex AI credentials in the sidebar to start chatting with RAG")

else:
    can_chat = bool(st.session_state.api_key)
    if not can_chat:
        st.info("👈 Please enter your Gemini API key in the sidebar to start chatting")

if can_chat:
    try:
        # Initialize chat session if needed
        if "chat_session" not in st.session_state:
            if st.session_state.chatbot_type == "sales":
                if st.session_state.use_rag:
                    st.session_state.chat_session = create_sales_chat(
                        rag=True,
                        project_id=st.session_state.project_id,
                        location=st.session_state.location,
                        corpus_id=st.session_state.corpus_id
                    )
                else:
                    st.session_state.chat_session = create_sales_chat(
                        rag=False,
                        api_key=st.session_state.api_key
                    )
            else:
                # Services chatbot
                st.session_state.chat_session = create_services_chat(
                    api_key=st.session_state.api_key
                )
        
        # Display chat messages using native Streamlit components
        for message in st.session_state.messages:
            # Keep agent avatar the same, use DiceBear for user avatar
            if message["role"] == "assistant":
                avatar = "https://media.licdn.com/dms/image/v2/C5603AQFQKW-lOyNbOA/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1516317569754?e=1756944000&v=beta&t=sTMOjNLrt7zCJhySpVUE1eoXLH0lXm2ZaLbd_7JIuVw"
            else:
                avatar = get_user_avatar()
            
            with st.chat_message(message["role"], avatar=avatar):
                if message["role"] == "assistant" and st.session_state.is_typing:
                    st.markdown('<div class="typing-animation">Typing</div>', unsafe_allow_html=True)
                else:
                    st.write(message["content"])
                    if "timestamp" in message:
                        st.markdown(f'<div class="message-timestamp">{message["timestamp"]}</div>', unsafe_allow_html=True)


        # Chat input
        placeholder_text = "How can I help you with your 3D printing needs?" if st.session_state.chatbot_type == "sales" else "What seems to be the problem with your device today?"
        if prompt := st.chat_input(placeholder_text):
            
            timestamp = datetime.now().strftime("%I:%M %p")
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "timestamp": timestamp
            })
            
            with st.chat_message("user", avatar=get_user_avatar()):
                st.write(prompt)
                st.markdown(f'<div class="message-timestamp">{timestamp}</div>', unsafe_allow_html=True)
            
            with st.chat_message("assistant", avatar="https://media.licdn.com/dms/image/v2/C5603AQFQKW-lOyNbOA/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1516317569754?e=1756944000&v=beta&t=sTMOjNLrt7zCJhySpVUE1eoXLH0lXm2ZaLbd_7JIuVw"):
                message_placeholder = st.empty()
                st.session_state.is_typing = True
                message_placeholder.markdown('<div class="typing-animation">Typing</div>', unsafe_allow_html=True)
                
                try:
                    if st.session_state.chatbot_type == "sales":
                        response = query_sales_llm(st.session_state.chat_session, prompt)
                        json_response = sales_extract_json_from_response(response.text)
                        if json_response:
                            create_opportunity(json_response)
                            if json_response.get('is_qualified') == 'Yes':
                                st.markdown("Ok we have everything we need. A sales rep will get back to you")
                            else:
                                st.markdown("Thank you for your inquiry. Please visit our website for any future purchases")
                    else:
                        response = query_services_llm(st.session_state.chat_session, prompt)
                        json_response = services_extract_json_from_response(response.text)
                        if json_response:
                            if json_response.get('job_name'):
                                create_case(json_response)
                                print('creating case')
                            elif json_response.get('printer_serial'):
                                print("I have the serial")
                                printer_serial = json_response.get('printer_serial')
                                print(printer_serial)
                                full_jobs, jobs_to_display = run_recent_jobs_query(printer_serial)
                                print(jobs_to_display)
                                if jobs_to_display == 'No jobs found':
                                    st.markdown("It does not appear that we have logs for your printer. Can you please upload them?")
                                else:
                                    st.markdown("Are these any of your prints?\n\n" + jobs_to_display)
                    timestamp = datetime.now().strftime("%I:%M %p")
                    st.session_state.is_typing = False
                    message_placeholder.write(response.text)
                    st.markdown(f'<div class="message-timestamp">{timestamp}</div>', unsafe_allow_html=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.text,
                        "timestamp": timestamp
                    })
                except Exception as e:
                    st.session_state.is_typing = False
                    message_placeholder.error(f"Error: {str(e)}")

    except Exception as e:
        st.error(f"Error: {str(e)}")
        if "chat_session" in st.session_state:
            del st.session_state.chat_session 