"""
This defines the host of the talkshow. He is managing the guests and the conversation.
"""

import os
from typing import List, Tuple, Generator, Union, Literal, Dict, Any    
from pydantic import BaseModel
import streamlit as st
from guest import Guest, GuestTemplate
from llm import load_prompt, generate_structured_response, load_txt_file
from config import mockup, max_tokens


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

    def display_message(self, message: str):
        """Display a message in the appropriate mode."""
        if self.display_mode == "console":
            print(message)
        else:  # streamlit
            st.write(message)

    def add_message(self, message: str, token_count: int):
        """
        Add a message to the conversation stack.
        """
        self.conversation.insert(0, (message, token_count))  # Insert at beginning since it's a stack (newest first)
        self.display_message(message)

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
