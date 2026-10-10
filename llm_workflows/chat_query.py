from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter()

class ChatRequest(BaseModel):
	query: str
	transcription: str

class ChatResponse(BaseModel):
	response: str


import os
from .llm import get_chat_model

def get_llm_response(query: str, transcription: str) -> str:
	try:
		llm = get_chat_model(temperature=0.2, max_tokens=512, timeout=30)
	except Exception as e:
		return f"Error initializing LLM: {str(e)}"

	# Prepare prompt from query and transcript
	# transcription is now always a direct string (business plan text)
	transcript_text = transcription if isinstance(transcription, str) else transcription.get('json_data', '')
	prompt = f"You are an expert assistant. Based on the following business plan transcript, answer the user's query.\n\nTranscript:\n{transcript_text}\n\nQuery: {query}\n\nProvide a concise and relevant answer."

	try:
		response = llm.invoke(prompt)
		return getattr(response, 'content', None) or str(response)
	except Exception as e:
		return f"Error generating response: {str(e)}"

import json
from fastapi import HTTPException

@router.post("/chat", response_model=ChatResponse)
async def chat_api(payload: ChatRequest):
	response = get_llm_response(payload.query, payload.transcription)
	return ChatResponse(response=response)
