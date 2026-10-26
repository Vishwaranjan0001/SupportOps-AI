"""FastAPI connects React and the LangGraph agent."""
import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.mcp import MCPAdapter
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent import build_graph
from db import (DATA, DEMO_CUSTOMER, init_db, new_conversation, conversation_exists,
                list_conversations, list_orders, list_tickets, list_refunds,
                decide_refund)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv('GROQ_API_KEY'):
        raise RuntimeError('Please set GROQ_API_KEY before starting the backend.')
    init_db()
    DATA.mkdir(exist_ok=True)
    # The adapter STARTS our MCP server as a local subprocess over stdio.
    async with MCPAdapter(Path(__file__).resolve().with_name('mcp_server.py')) as adapter:
        mcp_tools = await adapter.list_tools()
        async with AsyncSqliteSaver.from_conn_string(str(DATA / 'checkpoints.sqlite')) as saver:
            app.state.graph, app.state.tools = build_graph(mcp_tools, saver)
            app.state.locks = {}
            print('SupportOps ready. Tools:', app.state.tools)
            yield


app = FastAPI(title='SupportOps AI — Interview Demo', lifespan=lifespan)


class ChatBody(BaseModel):
    conversation_id: str = Field(min_length=36, max_length=36)
    message: str = Field(min_length=1, max_length=1500)


class ManagerDecision(BaseModel):
    approve: bool


@app.get('/health')
async def health(request: Request):
    return {'status': 'ok', 'mode': 'ONE_DEMO_CUSTOMER', 'tools': request.app.state.tools}


@app.post('/api/conversations')
async def create_chat():
    return {'conversation_id': new_conversation()}


@app.get('/api/conversations')
async def conversations():
    return {'conversations': list_conversations()}


def thread_id(chat_id):
    if not conversation_exists(chat_id, DEMO_CUSTOMER):
        raise HTTPException(404, 'Conversation not found')
    return f'{DEMO_CUSTOMER}:{chat_id}'


@app.get('/api/conversations/{chat_id}/messages')
async def chat_history(chat_id: str, request: Request):
    config = {'configurable': {'thread_id': thread_id(chat_id)}}
    checkpoint = await request.app.state.graph.aget_state(config)
    visible = []
    for msg in checkpoint.values.get('messages', []):
        if isinstance(msg, HumanMessage):
            visible.append({'role': 'user', 'text': str(msg.content)})
        elif isinstance(msg, AIMessage) and not msg.tool_calls and msg.content:
            visible.append({'role': 'assistant', 'text': str(msg.content)})
    return {'messages': visible}


@app.post('/api/chat')
async def chat(body: ChatBody, request: Request):
    user_message = body.message.strip()
    if not user_message:
        raise HTTPException(422, 'Message cannot be empty')
    name = thread_id(body.conversation_id)
    config = {'configurable': {'thread_id': name}, 'recursion_limit': 16}
    # One request at a time for the same conversation;
    lock = request.app.state.locks.setdefault(name, asyncio.Lock())
    async with lock:
        previous = await request.app.state.graph.aget_state(config)
        old_count = len(previous.values.get('messages', []))
        try:
            result = await request.app.state.graph.ainvoke({'messages': [HumanMessage(content=user_message)]}, config)
        except Exception as exc:
            print('Agent error:', repr(exc))
            raise HTTPException(502, 'Agent call failed. See backend terminal for details.')
    messages = result['messages']
    tool_names = [msg.name for msg in messages[old_count:] if isinstance(msg, ToolMessage)]
    answer = str(messages[-1].content)
    return {'conversation_id': body.conversation_id, 'reply': answer, 'tools_used': tool_names}


@app.get('/api/orders')
async def orders():
    return {'orders': list_orders()}





@app.get('/api/refunds')
async def refunds():
    return {'refunds': list_refunds()}


@app.get('/api/manager/refunds')
async def manager_queue():
    # DEMO ONLY: no manager login. Add authentication before any real deployment.
    return {'refunds': list_refunds(pending_only=True)}


@app.post('/api/manager/refunds/{request_id}')
async def manager_decide(request_id: int, body: ManagerDecision):
    result = decide_refund(request_id, body.approve)
    if 'error' in result:
        raise HTTPException(409, result['error'])
    return result


