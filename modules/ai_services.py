import asyncio
import json
import os
import sys
from typing import Optional

# Import the data module to get API keys and models
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))
from config.data import (
    AI_OPENAI_API_KEY, AI_GEMINI_API_KEY, AI_CLAUDE_API_KEY, 
    AI_GROK_API_KEY, AI_DEEPSEEK_API_KEY,
    AI_OPENAI_MODEL, AI_GEMINI_MODEL, AI_CLAUDE_MODEL,
    AI_GROK_MODEL, AI_DEEPSEEK_MODEL
)

class AIService:
    """Base class for AI services"""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
    
    async def generate_response(self, message: str) -> str:
        """Generate a response from the AI model"""
        if not self.api_key:
            return f"API key not found for {self.model_name}. Please make sure you pasted it in the Ax-Shell settings."
        
        try:
            # Run the API call in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._make_api_call_sync, message)
        except Exception as e:
            return f"Error communicating with {self.model_name}: {str(e)}"
    
    def _make_api_call_sync(self, message: str) -> str:
        """Synchronous version of the API call"""
        return self._make_api_call(message)
    
    async def _make_api_call(self, message: str) -> str:
        """Make the actual API call - to be implemented by subclasses"""
        raise NotImplementedError

class OpenAIService(AIService):
    """OpenAI/ChatGPT service"""
    
    def __init__(self):
        super().__init__(AI_OPENAI_API_KEY, "Chat GPT")
        self.model = AI_OPENAI_MODEL
    
    async def _make_api_call(self, message: str) -> str:
        try:
            import openai
            openai.api_key = self.api_key
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=[
                    {"role": "user", "content": message}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except ImportError:
            return "OpenAI library not installed. Please install it with: pip install openai"
        except Exception as e:
            return f"OpenAI API error: {str(e)}"

class GeminiService(AIService):
    """Google Gemini service"""
    
    def __init__(self):
        super().__init__(AI_GEMINI_API_KEY, "Gemini")
        self.model = AI_GEMINI_MODEL
    
    def _make_api_call_sync(self, message: str) -> str:
        """Synchronous API call for Gemini"""
        try:
            import google.generativeai as genai
            
            # Validate API key
            if not self.api_key or self.api_key.strip() == "":
                return "Gemini API key is empty. Please add your API key in the Ax-Shell settings."
            
            # Configure the API
            genai.configure(api_key=self.api_key)
            
            # Test the API key with a simple call
            try:
                model = genai.GenerativeModel(self.model)
                
                # Make the API call with error handling
                response = model.generate_content(message)
                
                # Check if response is valid and has content
                if response and hasattr(response, 'text') and response.text:
                    return response.text
                elif response and hasattr(response, 'parts') and response.parts:
                    # Handle response with parts
                    return response.parts[0].text
                elif response and hasattr(response, 'candidates') and response.candidates:
                    # Try accessing through candidates
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            return candidate.content.parts[0].text
                else:
                    return "Gemini API returned an empty response. Please try again."
                    
            except Exception as api_error:
                # Handle specific API errors
                error_str = str(api_error)
                if "API_KEY_INVALID" in error_str or "INVALID_ARGUMENT" in error_str:
                    return "Invalid Gemini API key. Please check your API key in the Ax-Shell settings."
                elif "QUOTA_EXCEEDED" in error_str:
                    return "Gemini API quota exceeded. Please check your usage limits."
                elif "PERMISSION_DENIED" in error_str:
                    return "Permission denied. Please check your Gemini API key permissions."
                elif "NoneType" in error_str and "from_call" in error_str:
                    return """Gemini API is currently experiencing issues. 

This appears to be a known issue with the Google Generative AI library. 

Please try:
1. Using a different AI model (ChatGPT, Claude, or Deepseek)
2. Updating the library: pip install --upgrade google-generativeai
3. Checking your internet connection

For now, I recommend using ChatGPT or Claude instead."""
                else:
                    return f"Gemini API error: {error_str}"
                
        except ImportError:
            return "Google Generative AI library not installed. Please install it with: pip install google-generativeai"
        except Exception as e:
            return f"Gemini configuration error: {str(e)}"
    
    async def _make_api_call(self, message: str) -> str:
        """Async wrapper for the synchronous API call"""
        return self._make_api_call_sync(message)

class ClaudeService(AIService):
    """Anthropic Claude service"""
    
    def __init__(self):
        super().__init__(AI_CLAUDE_API_KEY, "Claude")
        self.model = AI_CLAUDE_MODEL
    
    async def _make_api_call(self, message: str) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = await asyncio.to_thread(
                client.messages.create,
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            
            return response.content[0].text
        except ImportError:
            return "Anthropic library not installed. Please install it with: pip install anthropic"
        except Exception as e:
            return f"Claude API error: {str(e)}"

class GrokService(AIService):
    """xAI Grok service"""
    
    def __init__(self):
        super().__init__(AI_GROK_API_KEY, "Grok")
        self.model = AI_GROK_MODEL
    
    async def _make_api_call(self, message: str) -> str:
        # Grok API is not publicly available yet, so we'll return a placeholder
        return f"Grok API is not publicly available yet. Selected model: {self.model}. Please check back later for updates."

class DeepseekService(AIService):
    """Deepseek service"""
    
    def __init__(self):
        super().__init__(AI_DEEPSEEK_API_KEY, "Deepseek")
        self.model = AI_DEEPSEEK_MODEL
    
    async def _make_api_call(self, message: str) -> str:
        try:
            import openai
            openai.api_key = self.api_key
            openai.api_base = "https://api.deepseek.com/v1"
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=[
                    {"role": "user", "content": message}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except ImportError:
            return "OpenAI library not installed. Please install it with: pip install openai"
        except Exception as e:
            return f"Deepseek API error: {str(e)}"

class AIManager:
    """Manager class for all AI services"""
    
    def __init__(self):
        self.services = {
            "Chat GPT": OpenAIService(),
            "Gemini": GeminiService(),
            "Claude": ClaudeService(),
            "Grok": GrokService(),
            "Deepseek": DeepseekService(),
        }
    
    async def get_response(self, model_name: str, message: str) -> str:
        """Get a response from the specified AI model"""
        if model_name not in self.services:
            return f"Unknown AI model: {model_name}"
        
        service = self.services[model_name]
        return await service.generate_response(message)
    
    def get_available_models(self) -> list:
        """Get list of available models"""
        return list(self.services.keys())
    
    def has_api_key(self, model_name: str) -> bool:
        """Check if a model has an API key configured"""
        if model_name not in self.services:
            return False
        return bool(self.services[model_name].api_key)

# Global AI manager instance
ai_manager = AIManager() 