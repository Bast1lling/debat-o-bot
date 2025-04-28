"""
This defines the host of the talkshow. He is managing the guests and the conversation.
"""

import os
from typing import List, Tuple, Generator, Union, Literal, Dict, Any, Optional
from pydantic import BaseModel
from guest import Guest, GuestTemplate
from llm import load_prompt, stream_structured_response, load_txt_file, stream_simple_response, generate_structured_response, generate_simple_response
from config import mockup, max_tokens, model
import tiktoken
import threading
from queue import Queue
from sentence_transformers import SentenceTransformer
import numpy as np


class InviteResponse(BaseModel):
    guests: list[GuestTemplate]
    model_config = {
        "extra": "forbid",  # or 'allow' or 'ignore'
    }


class DebateResponse(BaseModel):
    guest_name: str
    message: str
    model_config = {
        "extra": "forbid",  # or 'allow' or 'ignore'
    }


class DebatePlan(BaseModel):
    steps: List[str]
    model_config = {
        "extra": "forbid",  # or 'allow' or 'ignore'
    }


class ReflectResponse(BaseModel):
    done: bool
    model_config = {
        "extra": "forbid",  # or 'allow' or 'ignore'
    }


class Host:
    def __init__(self, debate_topic: str, display_mode: Literal["console", "streamlit"] = "console"):
        self.debate_topic = debate_topic
        self.display_mode = display_mode
        self.guests = {}
        self.debate_plan = []
        self.conversation: List[Tuple[str, str, int]] = []  # Stack of messages and their token count, newest first
        self.name_encoder = SentenceTransformer('all-MiniLM-L6-v2')  # Initialize the encoder
        self.guest_name_embeddings = None  # Will store encoded guest names

    def update_guest_embeddings(self):
        """Update the guest name embeddings when guests list changes."""
        if self.guests:
            self.guest_name_embeddings = self.name_encoder.encode(list(self.guests.keys()))

    def add_message(self, message: str, name: str):
        """
        Add a message to the conversation stack.
        """
        token_count = self.count_tokens(message)
        self.conversation.insert(0, (message, name, token_count))  

    def retrieve_conversation(self) -> str:
        """
        Retrieve the conversation from the conversation stack.
        """
        tokens_so_far = 0
        messages = []
        for message, name, token_count in self.conversation:
            # Filter out guest introductions
            if name == "Host" and "Please welcome " in message:
                continue
            if tokens_so_far + token_count > max_tokens:
                break
            messages.append(f"{name}: {message}")
            tokens_so_far += token_count
        return "\n".join(messages)
    
    def add_guest(self, guest: Guest) -> None:
        """Add a guest if they're not already in the dict."""
        if guest not in self.guests:
            self.guests[guest.name] = guest

    def remove_guest(self, guest: Guest) -> None:
        """Remove a guest from the list."""
        if guest in self.guests:
            del self.guests[guest.name]

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
            response: Dict[str, Any] = generate_structured_response("Guests:", instructions=instructions, schema=InviteResponse) 

        self.guests = {guest_dict["name"]: Guest(**guest_dict) for guest_dict in response["guests"]}
        return self.guests
        
    def invite_guests_one_by_one(self) -> Generator[Guest, None, None]:
        """
        Invite the guests for the talkshow one by one.
        """
        instructions = load_prompt(
            os.path.join("host", "invite_instructions.txt"),
            {"debate_topic": self.debate_topic},
        )
        response: Generator[InviteResponse, None, None] = stream_structured_response("Guests:", instructions=instructions, schema=InviteResponse)

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
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    
    def get_guest_by_name(self, name: str) -> Optional[Guest]:
        """
        Get a guest by name using fuzzy matching with sentence encoders.
        
        Args:
            name: The name to search for
            
        Returns:
            The matching Guest object or None if no match found
        """
        if name in self.guests.keys():
            return self.guests[name]
        # Encode the input name
        name_embedding = self.name_encoder.encode([name])[0]
        
        # Calculate cosine similarities
        similarities = np.dot(self.guest_name_embeddings, name_embedding) / (
            np.linalg.norm(self.guest_name_embeddings, axis=1) * np.linalg.norm(name_embedding)
        )
        
        # Get the index of the most similar name
        best_match_idx = np.argmax(similarities)
        best_match_similarity = similarities[best_match_idx]
        
        # Only return a match if similarity is above threshold
        return self.guests[list(self.guests.keys())[best_match_idx]]

    def plan_debate(self, num_steps: int = 10) -> List[Tuple[str, str]]:
        instructions = load_prompt(
            os.path.join("host", "plan_instructions.txt"),
            {"debate_topic": self.debate_topic,
             "guests": [str(guest) for guest in self.guests],
             "num_steps": num_steps},
        )
        response: Dict[str, Any] = generate_structured_response("Response:", instructions=instructions, schema=DebatePlan)
        self.debate_plan = response["steps"]
    
    def run_debate_cycle(self, result_queue: Queue) -> None:
        """
        Run a single cycle of the debate and put results in the queue.
        """
        new_messages = []
        # First, ask the host whom to address
        conversation = self.retrieve_conversation()
        next_step = self.debate_plan[0]
        instructions = load_prompt(
            os.path.join("host", "debate_instructions.txt"),
            {"debate_topic": self.debate_topic,
             "debate_step": next_step,
             "guests": [str(guest) for guest in self.guests.values()],
             "guest_names": list(self.guests.keys()),
             "conversation": conversation},
        )
        print("Querying host")
        response: Dict[str, Any] = generate_structured_response("Response:", instructions=instructions, schema=DebateResponse)
        print(f"Response: {response}")
        guest_name = response["guest_name"]
        print(f"Guest name: {guest_name}")
        guest = self.get_guest_by_name(guest_name)
        message = response["message"]
        self.add_message(message, "Host")
        new_messages.append((message, "Your host"))
        
        # Then, ask the guest to respond
        conversation = self.retrieve_conversation()
        instructions = load_prompt(
            os.path.join("guest", "debate_instructions.txt"),
            {"debate_topic": self.debate_topic,
             "guest": str(guest),
             "conversation": conversation},
        )
        print("Querying guest")
        response: str = generate_simple_response("Response:", instructions=instructions)
        self.add_message(response, guest.name)
        new_messages.append((response, guest.name))
        
        # Put the results in the queue
        result_queue.put(new_messages)

    def reflect_on_debate(self, planning_queue: Queue) -> None:
        """
        Reflect on the debate and put the results in the queue.
        """
        if len(self.debate_plan) > 1:
            next_step = self.debate_plan[1]
        else:
            next_step = "No more steps"

        instructions = load_prompt(
            os.path.join("host", "reflect_instructions.txt"),
            {"debate_topic": self.debate_topic,
             "conversation": self.retrieve_conversation(),
             "current_step": self.debate_plan[0],
             "next_step": next_step},
        )
        response: Dict[str, Any] = generate_structured_response("Response:", instructions=instructions, schema=ReflectResponse)
        planning_queue.put(response["done"])
    
    def run_debate(self) -> Generator[Tuple[str, str], None, None]:
        """
        Run the debate.
        """
        self.update_guest_embeddings()
        # Start by introducing the topic and the guests
        welcome_message = f"Welcome to the debate on {self.debate_topic}."
        self.add_message(welcome_message, "Host")
        result_queue = Queue()
        planning_queue = Queue()
        new_messages = [(welcome_message, "Your host")]  # Start with welcome message
        done = False
        while self.debate_plan:  # Continue until debate plan is empty
            if done:
                if len(self.debate_plan) > 1:
                    self.debate_plan.pop(0)
                else:
                    self.debate_plan = []
                    break
            # Prepare next debate cycle in another thread
            debate_cycle_thread = threading.Thread(
                target=self.run_debate_cycle,
                daemon=True,
                args=(result_queue,)
            )
            debate_cycle_thread.start()
            
            # Reflect on the debate in another thread
            reflect_thread = threading.Thread(
                target=self.reflect_on_debate,
                daemon=True,
                args=(planning_queue,)
            )
            reflect_thread.start()
            
            # Yield messages from previous cycle
            for message, name in new_messages:
                yield message, name

            # Wait for the debate cycle to finish and get results
            debate_cycle_thread.join()
            new_messages = result_queue.get()

            # Wait for the reflection to finish and get results
            reflect_thread.join()
            done = planning_queue.get()
