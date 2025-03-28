import streamlit as st
from host import Host
from enum import Enum, auto


class State(Enum):
    TopicSelection = auto()
    GuestInvitation = auto() 
    DebateStart = auto()


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
            st.session_state.host.guests[index] = guest
            
            # Show a success message
            st.success("Profile updated!")


def main():
    st.title("🎪 Debate-O-Bot")
    st.write("Hello there, I'm the host of the talkshow.")
    
    # Initialize session state for host if it doesn't exist
    if 'host' not in st.session_state:
        topic = st.text_input("What do you want to discuss today?", value="Did Russia invade Ukraine?")
        if st.button("Start Discussion"):
            if topic:
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
                    st.experimental_rerun()
            else:
                st.warning("Please enter a topic to discuss.")
    else:
        # Display all guests
        print("displaying guests")
        for i, guest in enumerate(st.session_state.host.guests):
            display_guest_profile(guest, i)

if __name__ == "__main__":
    main() 