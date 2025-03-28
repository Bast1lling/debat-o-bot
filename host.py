"""
This defines the host of the talkshow. He is managing the guests and the conversation.
"""

import os
from typing import List, Tuple, Generator, Union, Literal, Dict, Any    
from pydantic import BaseModel
import streamlit as st
from guest import Guest, GuestTemplate
from llm import load_prompt, generate_structured_response, load_txt_file
from config import mockup, max_tokens, model
import tiktoken

class InviteResponse(BaseModel):
    guests: list[GuestTemplate]
    model_config = {
        "extra": "forbid",  # or 'allow' or 'ignore'
    }


class Host:
    def __init__(self, debate_topic: str, display_mode: Literal["console", "streamlit"] = "console"):
        self.debate_topic = debate_topic
        self.display_mode = display_mode
        self.guests = []  # Changed from set to list
        self.conversation: List[Tuple[str, int]] = []  # Stack of messages and their token count, newest first

    def add_message(self, message: str):
        """
        Add a message to the conversation stack.
        """
        token_count = self.count_tokens(message)
        self.conversation.insert(0, (message, token_count))  

    def retrieve_conversation(self) -> list[str]:
        """
        Retrieve the conversation from the conversation stack.
        """
        tokens_so_far = 0
        messages = []
        for message, token_count in self.conversation:
            if tokens_so_far + token_count > max_tokens:
                break
            messages.append(message)
            tokens_so_far += token_count
        return messages
    
    def add_guest(self, guest: Guest) -> None:
        """Add a guest if they're not already in the list."""
        if guest not in self.guests:
            self.guests.append(guest)

    def remove_guest(self, guest: Guest) -> None:
        """Remove a guest from the list."""
        if guest in self.guests:
            self.guests.remove(guest)

    def invite_guests_at_once(self) -> List[Guest]:
        """
        Fetch the entire list of guests at once.
        """
        instructions = load_prompt(
            os.path.join("host", "invite_instructions.txt"),
            {"debate_topic": self.debate_topic},
        )
        
        if mockup:
            response: Dict[str, Any] = load_txt_file(os.path.join("host", "example_response.txt"))
        else:
            response: Dict[str, Any] = generate_structured_response(instructions, InviteResponse, stream=False)

        self.guests = [Guest(**guest_dict) for guest_dict in response["guests"]]
        return self.guests
        
    
    def invite_guests_one_by_one(self) -> Generator[Guest, None, None]:
        """
        Invite the guests for the talkshow one by one.
        """
        instructions = load_prompt(
            os.path.join("host", "invite_instructions.txt"),
            {"debate_topic": self.debate_topic},
        )
        response: Generator[InviteResponse, None, None] = generate_structured_response(instructions, InviteResponse, stream=True)

        for guest_list in response:
            if guest_list["guests"]:
                guest_dict = guest_list["guests"][-1]
                guest = Guest(**guest_dict)
                self.add_guest(guest)  # Using new add_guest method
                yield guest

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a string based on the OpenAI model being used.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens in the text
        """
        # Get the encoding for the model
        if "gpt-4" in model:
            encoding = tiktoken.encoding_for_model("gpt-4")
        elif "gpt-3.5" in model:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            # Default to cl100k_base encoding which is used by most recent models
            encoding = tiktoken.get_encoding("cl100k_base")
            
        # Return token count
        return len(encoding.encode(text))
    
    def run_debate(self) -> Generator[Tuple[str, str], None, None]:
        """
        Run the debate.
        """
        # Start by introducing the topic and the guests
        welcome_message = f"Welcome to the debate on {self.debate_topic}."
        self.add_message(welcome_message)
        yield welcome_message, "Your host"

        # Introduce the guests
        for guest in self.guests:
            self.add_message(str(guest))
            yield str(guest), "Your host"

