"""Story content for the WBooks seed command.

Three original stories, each exactly eight pages long, written for the
ForestBook, IceBook and HoloBook reading atmospheres. Every story carries a
moral, three key lessons, and a small quiz with friendly explanations.
"""
from __future__ import annotations

from books.models import Book, Theme

STORIES = [
    {
        "title": "The Lantern in the Bramblewood",
        "age_group": Book.AgeGroup.EARLY,
        "theme": Theme.FOREST,
        "description": (
            "Twelve-year-old Ifeoma finds a lantern burning in the deepest part "
            "of the Bramblewood — a forest the village has stopped visiting. "
            "The lantern needs a keeper, and it has chosen her."
        ),
        "story_moral": "A light you keep for others keeps shining for you too.",
        "key_lessons": [
            "Being afraid of a place is not the same as being trapped by it.",
            "Small acts of care are the real magic in any forest.",
            "Being a keeper means tending the light, not owning it.",
        ],
        "pages": [
            "The Bramblewood had been called the green wall since Ifeoma was six, "
            "and nobody in her village walked into it after dark. On the last "
            "evening of the rains, a lantern was burning between the trees.",
            "It hung in the crook of an oak, glowing soft and steady, with no "
            "rope and no hand to hold it. Ifeoma counted to ten, told herself "
            "the light was only a reflection, and stepped over the threshold.",
            "Inside, the brambles parted like curtains. The air smelled of wet "
            "moss and cinnamon, and every fern turned its fronds towards the "
            "lantern as if greeting an old friend.",
            "A voice no bigger than a beetle said: \"I have waited a long time "
            "for a keeper. Somebody has to tend me, or I will go out.\" Ifeoma "
            "found the lantern heavy as a full basket of water.",
            "\"Then I will carry you,\" she said. \"But I want to know your name.\" "
            "\"I am called Small Light. I keep the paths warm so that no one "
            "gets lost in the green wall.\"",
            "The rain started again, harder this time. Small Light would not "
            "shine in the downpour, and Ifeoma's grandmother was waiting by the "
            "fire with soup going cold and worry in her eyes.",
            "Ifeoma held the lantern close and walked. The path that had looked "
            "like a tangle of bramble straightened into a clear, pale line "
            "exactly as wide as her two feet, and the light lit her way home.",
            "At the village gate she set Small Light on the windowsill. From "
            "then on, the green wall had a lantern in it, and every lost walker "
            "who followed its glow came out smiling.",
        ],
        "quiz": [
            {
                "question_text": "Why had the village stopped walking in the Bramblewood?",
                "options": [
                    "The trees were too old to walk between",
                    "It was called the green wall and nobody went in after dark",
                    "A pack of wolves lived there",
                    "The rain never stopped in that valley",
                ],
                "correct": 1,
                "explanation": "The wood was feared and avoided after dark — until Ifeoma went in anyway.",
            },
            {
                "question_text": "What did the lantern say its name was?",
                "options": ["Green Wall", "Small Light", "Cinnamon Fern", "Keeper"],
                "correct": 1,
                "explanation": "The little voice introduced itself as Small Light, keeper of the warm paths.",
            },
            {
                "question_text": "Why did the path straighten for Ifeoma?",
                "options": [
                    "The brambles were cut down that morning",
                    "Small Light lit the way for her",
                    "She followed the sound of the river",
                    "The lantern grew heavier and pushed the path flat",
                ],
                "correct": 1,
                "explanation": "Small Light showed the clear path home through the rain.",
            },
            {
                "question_text": "Where did Ifeoma leave Small Light at the end?",
                "options": [
                    "Back in the crook of the oak",
                    "Inside her grandmother's basket",
                    "On the village gate windowsill",
                    "In the soup pot",
                ],
                "correct": 2,
                "explanation": "She set it on the windowsill so every lost walker could find the light.",
            },
        ],
    },
    {
        "title": "The Glacier's Smallest Light",
        "age_group": Book.AgeGroup.MIDDLE,
        "theme": Theme.SNOW,
        "description": (
            "A research station on the far ice reports a light that moves after "
            "dark. Twelve-year-old Sora volunteers to ski out and find out what "
            "it is — and discovers the smallest thing on the glacier is carrying "
            "the largest thing of all."
        ),
        "story_moral": "The smallest light can hold up the biggest night.",
        "key_lessons": [
            "Paying attention beats guessing, especially in the dark.",
            "Brave is not the same as fearless — it is taking the next step anyway.",
            "Some lights only work when someone believes in them.",
        ],
        "pages": [
            "The station at Ridge Nine had one rule: never go past the third "
            "marker after dark. Sora read it on the board twice, then looked "
            "out at the white, where the aurora was stitching green ribbons "
            "across the sky.",
            "\"Something is walking out there,\" said Engineer Halvorsen, "
            "pointing at a light drifting between the pressure ridges. \"It has "
            "been out for nine nights. It stops when we watch, and it starts "
            "again when we don't.\"",
            "Sora took the spare headlamp, the emergency flare and a thermos of "
            "cocoa. She did not take the skidoo. A skidoo roars, and she had a "
            "feeling the small light would be frightened by noise.",
            "Three markers. Then four, and then nothing to count. The cold bit "
            "through her mittens, and the aurora dimmed, and for a moment the "
            "only brightness left was a single pinprick near the ice.",
            "It was a lantern no larger than her thumb, hanging inside a shelter "
            "of stacked ice blocks. Beside it lay a seal pup, no bigger than a "
            "cat, blinking slowly in the dark.",
            "\"You came,\" said a voice inside her hood. Sora turned around and "
            "found herself alone with the little lantern and the pup, and the "
            "voice was coming from the lantern.",
            "\"I am a lighthouse,\" it said. \"Very small, and very far from the "
            "sea. But this pup's mother cannot find us, and my light is the only "
            "thing she can see from the ridge.\"",
            "Sora cupped the lantern in both hands and walked in a wide circle "
            "on the ice, holding the light high, until a shadow on the ridge "
            "turned and came sliding down towards them. By dawn, both seals "
            "were warm, and the station wrote her name on the board by the door.",
        ],
        "quiz": [
            {
                "question_text": "What rule did the station have about the third marker?",
                "options": [
                    "Never go past it after dark",
                    "Never go past it before dawn",
                    "Only cross it with a skidoo",
                    "Mark it every morning",
                ],
                "correct": 0,
                "explanation": "The board said plainly: never go past the third marker after dark.",
            },
            {
                "question_text": "What was the light out on the ice doing?",
                "options": [
                    "Moving between the pressure ridges and stopping when watched",
                    "Signalling the station with colours",
                    "Falling slowly toward the crevasse",
                    "Lighting the way for the research team",
                ],
                "correct": 0,
                "explanation": "The light walked between the ridges and vanished whenever anyone looked.",
            },
            {
                "question_text": "Why did Sora leave the skidoo behind?",
                "options": [
                    "It had run out of fuel",
                    "It was too heavy to pull",
                    "She thought a skidoo would frighten the small light",
                    "Her grandmother needed it",
                ],
                "correct": 2,
                "explanation": "A skidoo roars, and Sora guessed the small light would be scared of noise.",
            },
            {
                "question_text": "What was the thumb-sized lantern really for?",
                "options": [
                    "To guide ships past the ice",
                    "To keep the station warm",
                    "To help the seal pup's mother find them",
                    "To mark the safe path home",
                ],
                "correct": 2,
                "explanation": "The little lighthouse existed so the pup's mother could spot them from the ridge.",
            },
        ],
    },
    {
        "title": "Signal from the Neon Sky",
        "age_group": Book.AgeGroup.MIDDLE,
        "theme": Theme.NEON,
        "description": (
            "In a city where every rooftop hums with holograms, fourteen-year-old "
            "Ines discovers one screen nobody else can read — and a message from "
            "a satellite that should have died thirty years ago."
        ),
        "story_moral": "Curiosity is a kind of courage, and it opens doors.",
        "key_lessons": [
            "Paying attention to what others dismiss can reveal something real.",
            "Asking for help is a skill, not a weakness.",
            "A single clear voice can change a whole city's story.",
        ],
        "pages": [
            "Every roof in Sable Heights carried a screen, and every screen "
            "shouted. Advertisements, weather, football scores, the price of "
            "oranges. Ines had learned to read the city the way you read a "
            "noticeboard in the rain — quickly, and mostly with her eyes shut.",
            "Except on the roof of the old tram depot, where one screen glowed "
            "in a colour nobody used. It showed a blue wire globe, and a "
            "number counting down: 41 hours, 40 hours, 39.",
            "Ines asked the city's help desk. The polite voice on the line said "
            "the screen was decommissioned in 1994, and asked her to stop "
            "climbing rooftops.",
            "So she did what any curious fourteen-year-old does next. She "
            "opened the depot roof, found the old receiver humming underneath, "
            "and read the serial plate: Relay Nine, for the Sky Rescue Network.",
            "\"Sky Rescue\" had shut down thirty years ago after the last of "
            "the weather satellites went quiet. The receiver was still "
            "listening. And on the countdown, the number beside it was a name: "
            "Kite.",
            "Ines had a bicycle, a soldering iron and eleven hours before the "
            "countdown ended. Her grandmother had said, \"Ask the mechanic on "
            "Fifth Street; he was my brother.\" He was eighty-four, and he had "
            "not opened that workshop in twenty years.",
            "Together they rebuilt the antenna while the neon city chimed the "
            "hour. The mechanic's hands were steady. Ines's were not, and he "
            "held the soldering iron for her when it mattered.",
            "At 3:14 in the morning the screen cleared and a boy's voice came "
            "through, thin with static: \"Relay Nine, please. My air is low.\" "
            "Ines looked at the count, at the number three, and spoke the only "
            "thing that mattered: \"We hear you. Hold on.\"",
        ],
        "quiz": [
            {
                "question_text": "What made the screen on the tram depot unusual?",
                "options": [
                    "It showed live football scores",
                    "It glowed in a colour nobody used",
                    "It was switched off every evening",
                    "It was the biggest screen in the city",
                ],
                "correct": 1,
                "explanation": "The odd blue wire globe appeared in a colour the rest of the city never used.",
            },
            {
                "question_text": "What did the serial plate on the receiver say?",
                "options": [
                    "Neon Weather Bureau",
                    "Sky Rescue Network",
                    "Sable Heights Transit",
                    "Relay Nine, retired",
                ],
                "correct": 1,
                "explanation": "The plate named Relay Nine, part of the long-dead Sky Rescue Network.",
            },
            {
                "question_text": "Whose name appeared beside the countdown?",
                "options": ["Marla", "Kite", "Ines", "Viktor"],
                "correct": 1,
                "explanation": "The countdown carried the name Kite, the stranded boy in the sky.",
            },
            {
                "question_text": "Why did Ines go to the mechanic on Fifth Street?",
                "options": [
                    "To buy a new bicycle",
                    "Because her grandmother told her he had helped her build things",
                    "Because the help desk sent her",
                    "To fix the tram",
                ],
                "correct": 1,
                "explanation": "Her grandmother remembered her brother, the mechanic, who had taught her to build.",
            },
        ],
    },
]
