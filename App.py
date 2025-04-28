import streamlit as st
from host import Host
from enum import Enum, auto
import time

from summarizer import summarize_debate


# Custom CSS to make the app use more screen space
st.set_page_config(
    layout="wide",  # Use wide layout
    initial_sidebar_state="collapsed",  # Collapse sidebar by default
    page_title="Debate-O-Bot",
    page_icon="🎪"
)

# Custom CSS to adjust the main content area
st.markdown("""
    <style>
        .main .block-container {
            max-width: 95%;
            padding-top: 2rem;
        }
        .stExpander {
            background-color: #f0f2f6;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .stChat {
            background-color: white;
            border-radius: 0.5rem;
            padding: 1rem;
        }
    </style>
""", unsafe_allow_html=True)


def display_guest_profile(guest, index):
    with st.container():
        st.markdown("---")  # Separator line
        st.subheader(f"🎤 {guest.name}")
        
        # Create a unique key for each guest's fields
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Name", guest.name, key=f"name_{index}")
            new_age = st.number_input("Age", min_value=1, max_value=120, value=guest.age, key=f"age_{index}")
            new_pronouns = st.text_input("Pronouns (subject/object)", f"{guest.pronouns['subject']}/{guest.pronouns['object']}", key=f"pronouns_{index}")
            new_occupation = st.text_input("Occupation", guest.occupation, key=f"occupation_{index}")
        
        with col2:
            new_background = st.text_area("Background", guest.background, key=f"background_{index}")
        
        # Update the guest object if any field has changed
        if (new_name != guest.name or 
            new_age != guest.age or 
            new_pronouns != f"{guest.pronouns['subject']}/{guest.pronouns['object']}" or
            new_occupation != guest.occupation or
            new_background != guest.background):
            old_guest = guest
            # Update the guest object
            guest.name = new_name
            guest.age = new_age
            pronouns_parts = new_pronouns.split("/")
            guest.pronouns = {"subject": pronouns_parts[0], "object": pronouns_parts[1]}
            guest.occupation = new_occupation
            guest.background = new_background
            
            # Update the guest in session state
            st.session_state.host.remove_guest(old_guest)
            st.session_state.host.add_guest(guest)
            st.session_state.host.update_guest_embeddings()
            
            # Show a success message
            st.success("Profile updated!")


def display_debate_overview(new_message, name):
    """Display the debate overview panel."""
    host = st.session_state.host
    with st.expander("📊 Debate Overview", expanded=True):
        # Topic section
        st.subheader("📌 Topic")
        st.write(f"**We're discussing:** {host.debate_topic}")
        
        # Guests section
        st.subheader("👥 Guests")
        for guest in host.guests.values():
            st.write(f"- {guest.name} ({guest.occupation})")
        
        # Summary section (placeholder for now)
        st.subheader("🎯 Debate Plan")
        for i, step in enumerate(host.debate_plan, 1):
            st.write(f"{i}. {step}")


def display_message_stream(message, name):
    """Display a message in a streaming fashion."""
    with st.container():
        # Create a message container with the speaker's name
        st.markdown(f"**{name}:**")
        message_container = st.empty()
        
        # Stream the message character by character
        displayed_message = ""
        for char in message:
            displayed_message += char
            message_container.markdown(displayed_message)
            time.sleep(0.005)  # Adjust speed as needed


def main():
    st.title("🎪 Debate-O-Bot")
    st.write("Hello there, I'm the host of the talkshow.")

    if not st.session_state.get("state"):
        st.session_state["state"] = "topic_selection"
    
    if st.session_state["state"] == "topic_selection":
        # Add a field to set the maximum number of debate rounds
        max_rounds = st.number_input("Number of debate rounds", min_value=1, max_value=20, value=10)
        topic = st.text_input("What do you want to discuss today?", value="Should I pour milk or pour cereal first?")
        if st.button("Start Discussion"):
            if topic:  
                st.session_state["max_rounds"] = max_rounds
                # Create a panel for the topic
                with st.expander("📌 Today's Topic", expanded=True):
                    st.write(f"**We're discussing:** {topic}")

                # Create a panel for the guests
                st.subheader("👥 Our Distinguished Guests")
                with st.spinner("Inviting guests..."):
                    st.session_state.host = Host(topic, display_mode="streamlit")
                    # Invite guests one by one with a placeholder
                    placeholder = st.empty()
                    for guest in st.session_state.host.invite_guests_one_by_one():
                        with placeholder.container():
                            st.write(f"Inviting {guest.name}...")
                    
                    print("done inviting guests")
                    # Clear the placeholder and rerun to switch to guest display
                    placeholder.empty()
                    st.session_state["state"] = "guest_display"
                    st.rerun()
            else:
                st.warning("Please enter a topic to discuss.")
    elif st.session_state["state"] == "guest_display":
        # Display all guests
        print("displaying guests")
        for i, guest in enumerate(st.session_state.host.guests.values()):
            display_guest_profile(guest, i)

        st.session_state.host.plan_debate(num_steps=st.session_state["max_rounds"])
        # Add a start debate button
        if st.button("Start Debate"):
            st.session_state["state"] = "debate"
            st.rerun()
    elif st.session_state["state"] == "debate":
        host = st.session_state.host
        
        # Create two columns for the panels
        col1, col2 = st.columns([2, 1])
        
        with col2:
            display_debate_overview(None, None)

        with col1:
            st.subheader("💬 Debate")
            # Create a container for the debate messages
            debate_container = st.empty()
            messages = []
            # Stream the debate messages
            with debate_container.container():
                for message, name in host.run_debate():
                    display_message_stream(message, name)
                    messages.append((message, name))
            st.session_state["messages"] = messages
            st.session_state["state"] = "debate_overview"
            st.rerun()
    elif st.session_state["state"] == "debate_overview":
        summary = summarize_debate(st.session_state["messages"], st.session_state.host.debate_topic)
        with st.expander("🎯 Debate Summary", expanded=True):
            st.write(summary)


if __name__ == "__main__":
    main() 