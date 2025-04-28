import os
import threading

from llm import generate_simple_response, load_prompt

def summarize_step(messages: list[tuple[str, str]], debate_topic: str) -> str:
    """
    Summarize a single step of the debate.
    """
    instructions = load_prompt(
        os.path.join("summarizer", "summarize_step.txt"),
        {"section": "\n".join(f"{name}: {message}" for message, name in messages),
         "debate_topic": debate_topic}
    )
    return generate_simple_response("Summary:", instructions=instructions)

def summarize_steps(messages: list[tuple[str, str]], debate_topic: str) -> str:
    """
    Summarize the steps of the debate.
    """
    # Reverse the messages list since newest messages are first
    messages = list(reversed(messages))
    
    # Split messages into groups, each starting with a Host message
    message_groups = []
    current_group = []
    
    for message, speaker in messages:
        if speaker == "Host" and current_group:
            message_groups.append(current_group)
            current_group = []
        current_group.append((message, speaker))
    
    # Add the last group if it exists
    if current_group:
        message_groups.append(current_group)
    
    # Create a thread for each group to summarize
    threads = []
    summaries = []
    
    for group in message_groups:
        thread = threading.Thread(
            target=lambda g: summaries.append(summarize_step(g, debate_topic)),
            args=(group,)
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Combine all summaries with their indices
    return "\n\n".join(f"{i+1}. {summary}" for i, summary in enumerate(summaries))

def summarize_debate(messages: list[tuple[str, str]], debate_topic: str) -> str:
    """
    Summarize the entire debate.
    """
    instructions = load_prompt(
        os.path.join("summarizer", "summarize_debate.txt"),
        {"sections": summarize_steps(messages, debate_topic),
         "debate_topic": debate_topic}
    )
    return generate_simple_response("Summary:", instructions=instructions)
