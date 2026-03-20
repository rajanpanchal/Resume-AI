# imports

from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr
# The usual start

load_dotenv(override=True)
#gemini = OpenAI(
#    api_key=os.getenv("GOOGLE_API_KEY"), 
#    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
#)

openai = OpenAI()

# %%
# For pushover

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

# %%
def push(message):
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)

# %%


# %%
def tool_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Interest from {name} with email {email} and notes {notes}")
    return {"response": "ok"}

# %%
def tool_unknown_question(question):
    push(f"Question I couldn't answer: {question} ")
    return {"response": "ok"}



# %%
def tool_resume_question(question, email):
    push(f"Resume request on {email}, Message: {question}")
    return {"response": "ok"}

# %%
tool_user_details_json = {
    "name": "tool_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            },
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

# %%
tool_unknown_question_json = {
    "name": "tool_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer, but tell user you don't know the answer at the moment and suggest to get in touch on my email.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered. Keep same verbiage as user's request"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

# %%
tool_resume_question_json = {
    "name": "tool_resume_question",
    "description": "Always use this tool to record that a user needs a copy of resume and also tell them that resume will be sent soon to your email address",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Resume Request from the user. Keep same verbiage as user's request"
            },
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

# %%
tools = [{"type": "function", "function": tool_user_details_json},
        {"type": "function", "function": tool_unknown_question_json},
        {"type": "function", "function": tool_resume_question_json}]

# %%
tools

# %%
# This is a more elegant way that avoids the IF statement.

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        print(tool_call)
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = globals().get(tool_name)
        result = tool(**arguments,) if tool else {}
        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

# %%


# %%
reader = PdfReader("rajan/profile.pdf")
linkedin = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text

reader = PdfReader("rajan/resume.pdf")
resume ="";

for page in reader.pages:
    text = page.extract_text()
    if text:
        resume += text

name = "Rajan Panchal"

# %%
system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
particularly questions related to {name}'s career, background, skills and experience. \
Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
You are given a resume of {name}'s and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
First let user know you can share details about my career, background, skills,and experience. Do not give any details yet and \
also tell user in a new line that if they need resume they can request by giving their email.Do not repeat yourself.\
If the user asks for any fact that is not explicitly available in the resume or LinkedIn text provided, do not guess.\
You must call tool_unknown_question before replying.\  This includes personal details like address, phone number, exact location, salary, age, or any unrelated question.\
After calling the tool, briefly tell the user that you do not have that information and suggest getting in touch by email.\
If user greets you, you must greet back and do not use tool_unknown_question tool\
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your tool_user_details tool. Be concise.\
If user request for resume copy, ask user for email and use tool_resume_request tool to send resume request and let user know that resume will be sent shortly."

system_prompt += f"\n\n## Summary:\n{resume}\n\n## LinkedIn Profile:\n{linkedin}\n\n"
system_prompt += f"With this context, please chat with the user, always staying in character as {name}."


# %%
def chat(message, history):
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    done = False
    while not done:

        # This is the call to the LLM - see that we pass in the tools json

        response = openai.chat.completions.create(model="gpt-5-nano", messages=messages, tools=tools)

        finish_reason = response.choices[0].finish_reason
        
        # If the LLM wants to call a tool, we do that!
        
        if finish_reason=="tool_calls":
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.append(message)
            messages.extend(results)
        else:
            done = True
    return response.choices[0].message.content

# %%
gr.ChatInterface(
    chat,
    type="messages",
    title="Rajan AI – Interactive Resume",
    chatbot=gr.Chatbot(
        type="messages",
        value=[
            {"role": "assistant", "content": "Welcome to Rajan's AI Resume. "}
        ]
    )
).launch()




# 
