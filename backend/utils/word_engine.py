"""
backend/utils/word_engine.py

Advanced Letter-to-Word Construction Engine.
Provides prefix autocomplete, fuzzy spell-autocorrection (Levenshtein distance),
and dictionary validation for fingerspelled sign streams.
"""

# Core conversational and sign language vocabulary dictionary
DICTIONARY = {
    # Greetings & Courtesy
    "HELLO", "HI", "HEY", "GOOD", "MORNING", "NIGHT", "AFTERNOON", "EVENING",
    "PLEASE", "THANK", "THANKS", "WELCOME", "SORRY", "EXCUSE", "PARDON",
    "GOODBYE", "BYE", "SEE", "LATER", "NICE", "MEET", "FRIEND", "LOVE",

    # Questions & Responses
    "YES", "NO", "MAYBE", "OKAY", "OK", "SURE", "FINE", "TRUE", "FALSE",
    "WHAT", "WHERE", "WHO", "WHY", "WHEN", "HOW", "WHICH",

    # Pronouns & People
    "I", "ME", "MY", "YOU", "YOUR", "WE", "US", "OUR", "THEY", "THEM", "HE", "HIM",
    "SHE", "HER", "IT", "MAN", "WOMAN", "CHILD", "BOY", "GIRL", "MOTHER", "FATHER",
    "BROTHER", "SISTER", "DOCTOR", "NURSE", "POLICE", "TEACHER", "STUDENT",

    # Needs, Actions & Daily Life
    "WATER", "FOOD", "EAT", "DRINK", "HUNGRY", "THIRSTY", "HELP", "NEED", "WANT",
    "LIKE", "GO", "COME", "STAY", "WAIT", "SLEEP", "WAKE", "REST", "WORK", "STUDY",
    "HOSPITAL", "BATHROOM", "TOILET", "HOME", "HOUSE", "STORE", "CAR", "BUS", "TRAIN",
    "TIME", "TODAY", "TOMORROW", "YESTERDAY", "NOW", "SOON", "LATER", "NAME",

    # Common English words for fingerspelling
    "ABOUT", "AFTER", "AGAIN", "ALL", "ALSO", "AND", "ANY", "APPLE", "ASK", "BAD",
    "BEAUTIFUL", "BECAUSE", "BEFORE", "BEST", "BETTER", "BIG", "BOOK", "CALL", "CAN",
    "CARE", "CHANGE", "CLEAN", "COLD", "DAY", "DEAF", "DO", "EASY", "EVERY", "FAMILY",
    "FEEL", "FIRST", "GIVE", "GREAT", "HAPPY", "HAVE", "HEAR", "HOT", "IMPORTANT",
    "KEEP", "KNOW", "LEARN", "LIFE", "LITTLE", "LOOK", "MAKE", "MANY", "MUTE", "NEW",
    "OLD", "OPEN", "PLAY", "READ", "RIGHT", "SAD", "SAY", "SIGN", "SMALL", "SMILE",
    "SPEAK", "START", "STOP", "STRONG", "TAKE", "TALK", "TELL", "THINK", "UNDERSTAND",
    "VERY", "WALK", "WATCH", "WAY", "WELL", "WRITE", "WRONG", "YEAR",
}


def levenshtein_distance(s1, s2):
    """Calculates Levenshtein edit distance between two uppercase strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def autocomplete_prefix(prefix, max_results=5):
    """
    Returns dictionary words matching the given prefix.
    """
    if not prefix:
        return []
    p = prefix.strip().upper()
    matches = [w for w in DICTIONARY if w.startswith(p)]
    # Sort matches by length so shortest/most direct words come first
    matches.sort(key=lambda w: (len(w), w))
    return matches[:max_results]


def autocorrect_word(word, max_distance=2):
    """
    Finds the closest dictionary word if the input has spelling or classification errors.
    e.g. 'THAMKS' -> 'THANKS', 'HELO' -> 'HELLO', 'WATR' -> 'WATER'
    """
    if not word:
        return word
    w = word.strip().upper()
    if w in DICTIONARY:
        return w

    best_word = w
    best_dist = max_distance + 1

    for dict_word in DICTIONARY:
        # Optimization: skip words with large length differences
        if abs(len(dict_word) - len(w)) > max_distance:
            continue
        dist = levenshtein_distance(w, dict_word)
        if dist < best_dist:
            best_dist = dist
            best_word = dict_word

    if best_dist <= max_distance:
        return best_word
    return w


def construct_word_from_letters(letters_list):
    """
    Assembles a list of individual letter tokens into a finished word,
    applying spell-checking and autocomplete suggestions.
    """
    if not letters_list:
        return {"raw": "", "corrected": "", "suggestions": []}

    raw_word = "".join(letters_list).strip().upper()
    corrected = autocorrect_word(raw_word)
    suggestions = autocomplete_prefix(raw_word, max_results=4)

    if corrected not in suggestions and corrected != raw_word:
        suggestions.insert(0, corrected)

    return {
        "raw": raw_word,
        "corrected": corrected,
        "suggestions": suggestions,
    }


# Context-aware next word / phrase predictive transitions
PREDICTIVE_PAIRS = {
    "HELLO": ["HOW ARE YOU", "NICE TO MEET YOU", "FRIEND", "GOOD MORNING"],
    "HI": ["HOW ARE YOU", "NICE TO MEET YOU", "FRIEND"],
    "GOOD": ["MORNING", "AFTERNOON", "NIGHT", "JOB", "LUCK"],
    "THANK": ["YOU", "YOU VERY MUCH", "AGAIN"],
    "THANKS": ["FOR YOUR HELP", "A LOT", "VERY MUCH"],
    "PLEASE": ["HELP ME", "GIVE ME WATER", "WAIT", "REPEAT"],
    "HOW": ["ARE YOU", "MUCH", "DO YOU DO", "CAN I HELP"],
    "WHAT": ["IS YOUR NAME", "TIME IS IT", "HAPPENED", "DO YOU NEED"],
    "WHERE": ["IS THE RESTROOM", "IS THE BATHROOM", "ARE WE GOING", "IS THE HOSPITAL"],
    "WHO": ["IS THAT", "ARE YOU", "CAN HELP"],
    "WHY": ["NOT", "IS THAT HAPPENING", "ARE YOU HERE"],
    "I": ["WANT", "NEED", "FEEL", "AM", "LIKE", "DONT UNDERSTAND"],
    "ME": ["WANT", "NEED", "HELP", "FEEL SICK"],
    "YOU": ["WANT", "NEED", "KNOW", "HELP ME", "ARE WELCOME"],
    "NICE": ["TO MEET YOU", "DAY", "WEATHER"],
    "HELP": ["ME PLEASE", "NEEDED", "DOCTOR", "EMERGENCY"],
    "NEED": ["WATER", "FOOD", "DOCTOR", "HELP", "MEDICINE", "REST"],
    "WANT": ["WATER", "FOOD", "TO GO HOME", "TO SLEEP", "HELP"],
    "FEEL": ["GOOD", "BAD", "SICK", "TIRED", "HAPPY", "SAD", "PAIN"],
}

COMMON_GLOSS_PHRASES = {
    ("HELLO", "HOW", "YOU"): "Hello, how are you?",
    ("NICE", "MEET", "YOU"): "Nice to meet you.",
    ("YOU", "NAME", "WHAT"): "What is your name?",
    ("NAME", "YOU", "WHAT"): "What is your name?",
    ("MY", "NAME"): "My name is...",
    ("ME", "WANT", "WATER"): "I would like some water, please.",
    ("I", "WANT", "WATER"): "I would like some water.",
    ("ME", "NEED", "HELP"): "I need some help, please.",
    ("I", "NEED", "HELP"): "I need help.",
    ("WHERE", "BATHROOM"): "Where is the bathroom?",
    ("WHERE", "TOILET"): "Where is the restroom?",
    ("WHERE", "HOSPITAL"): "Where is the nearest hospital?",
    ("THANK", "YOU"): "Thank you very much!",
    ("PLEASE", "HELP"): "Please help me.",
    ("SORRY", "NOT", "UNDERSTAND"): "I'm sorry, I don't understand.",
    ("SEE", "YOU", "LATER"): "See you later!",
    ("GOOD", "MORNING"): "Good morning!",
    ("GOOD", "NIGHT"): "Good night!",
}


def gloss_to_sentence(gloss_text):
    """
    Transforms ASL/ISL sign glosses into fluent English sentences.
    Handles WH-questions, pronoun alignment, tense, and punctuation.
    """
    if not gloss_text:
        return ""
    
    tokens = [t.strip().upper() for t in gloss_text.replace(",", " ").split() if t.strip()]
    if not tokens:
        return ""

    # Check exact phrase matches
    t_tuple = tuple(tokens)
    if t_tuple in COMMON_GLOSS_PHRASES:
        return COMMON_GLOSS_PHRASES[t_tuple]

    # Sub-phrase match check
    for length in range(min(len(tokens), 4), 1, -1):
        sub = tuple(tokens[:length])
        if sub in COMMON_GLOSS_PHRASES:
            rest = " ".join(tokens[length:])
            base = COMMON_GLOSS_PHRASES[sub].rstrip(".?!")
            if rest:
                return f"{base} {rest.lower()}."
            return COMMON_GLOSS_PHRASES[sub]

    # Rule-based grammatical alignment
    is_question = any(q in tokens for q in ["WHAT", "WHERE", "WHO", "WHY", "WHEN", "HOW", "WHICH"])
    
    # Pronoun mapping
    pronoun_map = {
        "ME": "I",
        "MY": "my",
        "YOU": "you",
        "YOUR": "your",
        "HE": "he",
        "SHE": "she",
        "THEY": "they",
        "WE": "we",
    }

    # Rearrange if WH-word is at the end (standard ASL syntax: [YOU NAME WHAT] -> [WHAT YOUR NAME])
    if is_question and len(tokens) >= 2 and tokens[-1] in ["WHAT", "WHERE", "WHO", "WHY", "WHEN", "HOW"]:
        wh_word = tokens.pop()
        tokens.insert(0, wh_word)

    words = []
    for i, token in enumerate(tokens):
        if token in pronoun_map:
            words.append(pronoun_map[token])
        else:
            words.append(token.lower())

    sentence = " ".join(words)

    # Clean capitalization & punctuation
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
        if is_question:
            if not sentence.endswith("?"):
                sentence += "?"
        else:
            if not sentence.endswith((".", "!", "?")):
                sentence += "."

    return sentence


def get_predictive_suggestions(gloss_text, max_suggestions=4):
    """
    Returns next probable words/phrases based on current sign context.
    """
    if not gloss_text:
        return ["HELLO", "THANK YOU", "PLEASE", "HELP", "HOW ARE YOU"]

    tokens = [t.strip().upper() for t in gloss_text.replace(",", " ").split() if t.strip()]
    if not tokens:
        return ["HELLO", "THANK YOU", "PLEASE", "HELP"]

    last_token = tokens[-1]
    suggestions = PREDICTIVE_PAIRS.get(last_token, [])

    if not suggestions and len(tokens) >= 2:
        last_two = f"{tokens[-2]} {tokens[-1]}"
        suggestions = PREDICTIVE_PAIRS.get(last_two, [])

    if not suggestions:
        # Fallback to general conversational tokens
        suggestions = ["THANK YOU", "PLEASE", "HELP", "YES", "NO", "GOOD"]

    # Filter out what's already current
    filtered = [s for s in suggestions if s != last_token]
    return filtered[:max_suggestions]

