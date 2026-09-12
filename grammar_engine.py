"""
grammar_engine.py

Translates Sign Language Gloss (keyword sequences) into fluent, natural,
grammatically correct spoken English sentences, and provides predictive
conversational sentence suggestions.
"""

import re

# Direct phrase and template mappings for common Sign Gloss patterns
GLOSS_TEMPLATES = [
    # Wh-Questions
    (r"^(?:YOU\s+)?NAME\s+WHAT$", "What is your name?"),
    (r"^WHAT\s+(?:YOU\s+)?NAME$", "What is your name?"),
    (r"^(?:YOUR\s+)?NAME\s+WHAT$", "What is your name?"),
    (r"^(?:WHERE\s+)?BATHROOM\s+(?:WHERE)?$", "Where is the bathroom, please?"),
    (r"^(?:WHERE\s+)?HOSPITAL\s+(?:WHERE)?$", "Where is the hospital?"),
    (r"^(?:WHERE\s+)?DOCTOR\s+(?:WHERE)?$", "Where can I find a doctor?"),
    (r"^(?:WHERE\s+)?WATER\s+(?:WHERE)?$", "Where can I get some water?"),
    (r"^(?:WHERE\s+)?FOOD\s+(?:WHERE)?$", "Where can I find food?"),
    (r"^(?:WHAT\s+)?TIME\s+(?:WHAT)?$", "What time is it?"),
    (r"^HOW\s+YOU$", "How are you doing?"),
    (r"^HOW\s+ARE\s+YOU$", "How are you doing?"),
    (r"^YOU\s+OKAY?$", "Are you okay?"),
    (r"^WHO\s+YOU$", "Who are you?"),

    # Greetings & Courtesy
    (r"^HELLO$", "Hello!"),
    (r"^HELLO\s+FRIEND$", "Hello, my friend!"),
    (r"^GOOD\s+MORNING$", "Good morning!"),
    (r"^GOOD\s+NIGHT$", "Good night!"),
    (r"^GOOD\s+JOB$", "Good job, well done!"),
    (r"^THANK\s+YOU$", "Thank you very much!"),
    (r"^THANKS$", "Thank you!"),
    (r"^THANKS\s+HELP$", "Thank you for your help!"),
    (r"^THANK\s+YOU\s+HELP$", "Thank you for your help!"),
    (r"^PLEASE\s+HELP$", "Please help me."),
    (r"^PLEASE\s+HELP\s+ME$", "Please help me."),
    (r"^HELP\s+ME$", "Please help me."),
    (r"^SORRY$", "I am so sorry."),
    (r"^SORRY\s+LATE$", "I am sorry for being late."),
    (r"^WELCOME$", "You are welcome!"),
    (r"^NICE\s+(?:TO\s+)?MEET\s+(?:YOU)?$", "Nice to meet you!"),
    (r"^GOODBYE$", "Goodbye, take care!"),
    (r"^SEE\s+YOU$", "See you later!"),

    # Needs & Requests
    (r"^(?:ME|I)\s+(?:NEED|WANT)\s+WATER$", "I need some water, please."),
    (r"^(?:ME|I)\s+(?:NEED|WANT)\s+FOOD$", "I am hungry and need some food."),
    (r"^(?:ME|I)\s+(?:NEED|WANT)\s+HELP$", "I need some assistance, please."),
    (r"^(?:ME|I)\s+(?:NEED|WANT)\s+DOCTOR$", "I need to see a doctor immediately."),
    (r"^(?:ME|I)\s+FEEL\s+SAD$", "I am feeling sad today."),
    (r"^(?:ME|I)\s+FEEL\s+HAPPY$", "I am feeling very happy today."),
    (r"^(?:ME|I)\s+FEEL\s+BAD$", "I am not feeling well."),
    (r"^(?:ME|I)\s+FEEL\s+GOOD$", "I am feeling great."),
    (r"^(?:ME|I)\s+LOVE\s+YOU$", "I love you."),
    (r"^LOVE\s+YOU$", "I love you."),
    (r"^NO\s+PROBLEM$", "No problem at all!"),
]

# Predictive suggestions based on starting words/context
PREDICTIVE_CHIPS = {
    "HELLO": [
        "Hello! How are you doing?",
        "Hello, my name is Srijan.",
        "Hello, nice to meet you!",
    ],
    "HI": [
        "Hi there! How are you?",
        "Hi, nice to meet you!",
        "Hi, can you help me?",
    ],
    "HELP": [
        "Please help me, I need assistance.",
        "Can you help me find directions?",
        "I need urgent medical help.",
    ],
    "WATER": [
        "Can I please have a glass of water?",
        "Where can I find drinking water?",
        "I am thirsty, thank you.",
    ],
    "FOOD": [
        "Where can I find something to eat?",
        "I am hungry, is there food nearby?",
        "Thank you for the meal.",
    ],
    "THANK": [
        "Thank you very much for your help!",
        "Thank you, have a wonderful day!",
        "Thanks a lot, I appreciate it.",
    ],
    "THANKS": [
        "Thank you so much!",
        "Thanks for helping me out.",
        "Thanks, see you later!",
    ],
    "NAME": [
        "What is your name?",
        "My name is pleased to meet you.",
        "Can you spell your name for me?",
    ],
    "WHERE": [
        "Where is the nearest bathroom?",
        "Where can I get help?",
        "Where is the exit?",
    ],
    "WHAT": [
        "What is your name?",
        "What time is it right now?",
        "What happened?",
    ],
    "SORRY": [
        "I am sorry, I am deaf/mute.",
        "Sorry for the misunderstanding.",
        "I apologize for the inconvenience.",
    ],
    "PLEASE": [
        "Please help me with this.",
        "Please write it down for me.",
        "Please give me a moment.",
    ],
    "NICE": [
        "Nice to meet you!",
        "It was nice talking to you.",
        "Have a nice day!",
    ],
    "DOCTOR": [
        "I need to see a doctor immediately.",
        "Where is the nearest hospital?",
        "Please call an ambulance for me.",
    ],
}


def clean_tokens(input_val):
    """Parses input string or list into a clean uppercase token list."""
    if isinstance(input_val, str):
        tokens = [t.strip().upper() for t in input_val.split() if t.strip()]
    elif isinstance(input_val, (list, tuple)):
        tokens = []
        for item in input_val:
            if isinstance(item, str):
                tokens.extend([t.strip().upper() for t in item.split() if t.strip()])
    else:
        tokens = []
    return tokens


def gloss_to_sentence(input_val):
    """
    Translates a sequence of sign gloss words into a natural, grammatically
    fluent spoken English sentence.
    """
    tokens = clean_tokens(input_val)
    if not tokens:
        return ""

    raw_text = " ".join(tokens)

    # 1. Check exact regex templates
    for pattern, sentence in GLOSS_TEMPLATES:
        if re.match(pattern, raw_text, re.IGNORECASE):
            return sentence

    # 2. Heuristic Grammar Synthesis
    # Convert Sign Pronouns and Words
    words = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # First person subject
        if tok == "ME":
            words.append("I" if i == 0 or (i > 0 and tokens[i - 1] in ("AND", "BUT")) else "me")
        elif tok == "MY":
            words.append("my")
        elif tok == "YOU":
            words.append("you")
        elif tok == "YOUR":
            words.append("your")
        elif tok == "HELP":
            if i == 0:
                words.append("Please help")
            else:
                words.append("help")
        elif tok == "WANT":
            words.append("would like" if i == 1 else "want")
        elif tok == "NEED":
            words.append("need")
        elif tok == "WATER":
            words.append("some water")
        elif tok == "FOOD":
            words.append("some food")
        else:
            words.append(tok.lower())
        i += 1

    sentence = " ".join(words)

    # Capitalize first letter
    sentence = sentence[0].upper() + sentence[1:] if sentence else ""

    # Smart Punctuation
    first_word = tokens[0]
    last_word = tokens[-1]
    if first_word in ("WHAT", "WHERE", "WHO", "WHY", "HOW", "WHEN") or last_word in ("WHAT", "WHERE", "WHO", "HOW", "OKAY"):
        if not sentence.endswith("?"):
            sentence += "?"
    elif first_word in ("HELLO", "HI", "THANK", "THANKS", "WELCOME", "GOODBYE"):
        if not sentence.endswith("!") and not sentence.endswith("."):
            sentence += "!"
    else:
        if not sentence.endswith(".") and not sentence.endswith("?") and not sentence.endswith("!"):
            sentence += "."

    return sentence


def get_predictive_suggestions(input_val):
    """
    Returns 2-4 context-aware conversational sentence suggestions
    based on the current sign words.
    """
    tokens = clean_tokens(input_val)
    if not tokens:
        return [
            "Hello! How are you doing?",
            "Please help me, I use sign language.",
            "Thank you very much!",
        ]

    # Check the last signed word or first word for contextual matches
    for tok in reversed(tokens):
        if tok in PREDICTIVE_CHIPS:
            return PREDICTIVE_CHIPS[tok]

    for tok in tokens:
        if tok in PREDICTIVE_CHIPS:
            return PREDICTIVE_CHIPS[tok]

    # Default general suggestions incorporating the current sentence
    current_sentence = gloss_to_sentence(tokens)
    return [
        current_sentence,
        f"{current_sentence} Thank you.",
        f"Please, {current_sentence.lower()}",
    ]
