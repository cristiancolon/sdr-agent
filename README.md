# Sales Assistant Chat Application

A Streamlit-based chat application that uses Google's Gemini AI to assist with sales inquiries.

## Prerequisites

- Python 3.8 or higher
- A Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Setup Instructions

### For Mac Users

1. Open Terminal and clone the repository:
   ```bash
   git clone <repository-url>
   cd sdr-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   ```bash
   cp env.example .env
   ```
   Then edit the `.env` file and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. Run the application:
   ```bash
   streamlit run app.py
   ```

### For Windows Users

1. Open Command Prompt or PowerShell and clone the repository:
   ```cmd
   git clone <repository-url>
   cd sdr-agent
   ```

2. Create and activate a virtual environment:
   ```cmd
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. Install the required packages:
   ```cmd
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   ```cmd
   copy env.example .env
   ```
   Then edit the `.env` file and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. Run the application:
   ```cmd
   streamlit run app.py
   ```

## Using the Application

1. After starting the application, it will open in your default web browser
2. If you haven't set the API key in `.env`, you can enter it directly in the sidebar
3. Start chatting with the AI sales assistant using the chat interface
4. Use the sidebar to:
   - Clear the chat history
   - Check backend connection status
   - View instructions

## Project Structure

```
sdr-agent/
├── app/
│   └── static/         # Static assets
├── backend/
│   └── chat.py        # Chat backend implementation
├── app.py             # Main Streamlit application
├── env.example        # Example environment variables
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Troubleshooting

- If you see a connection error, verify your API key is correct
- If the virtual environment activation fails, make sure you're using the correct path separator for your OS
- For Windows users: If you get permission errors, try running PowerShell as administrator

## Notes

- Each user gets their own chat session, even if sharing the same API key
- Chat history is stored in the browser session and will be cleared when you refresh the page
- The application can be deployed to Streamlit Cloud for public access 