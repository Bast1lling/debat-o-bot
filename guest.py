"""
This defines the guests of the talkshow. They are the ones who will be interviewed.
"""

from pydantic import BaseModel


class Guest:
    def __init__(
        self, name: str, age: int, pronouns: str, occupation: str, background: str
    ):
        self.name = name
        self.age = age
        pronouns_parts = pronouns.split("/")
        self.pronouns = {"subject": pronouns_parts[0], "object": pronouns_parts[1]}
        self.occupation = occupation
        self.background = background

    def __str__(self):
        return (
            f"Please welcome {self.name}, a {self.age}-year-old {self.occupation}. "
            f"{self.pronouns['subject']} has the following background: {self.background}"
        )

    def __eq__(self, other):
        if not isinstance(other, Guest):
            return False
        return (self.name == other.name and
                self.age == other.age and 
                self.pronouns == other.pronouns and
                self.occupation == other.occupation and
                self.background == other.background)

    def __hash__(self):
        return hash((self.name, self.age, tuple(self.pronouns.values()), self.occupation, self.background))

class GuestTemplate(BaseModel):
    name: str
    age: int
    pronouns: str
    occupation: str
    background: str

    model_config = {
        "extra": "forbid",  # or 'allow' or 'ignore'
        "allow_inf_nan": False,
        # https://docs.pydantic.dev/latest/api/config/
    }
