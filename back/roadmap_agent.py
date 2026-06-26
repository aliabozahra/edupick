"""
roadmap_agent.py — Phase 3
CrewAI-based roadmap generator with Pydantic output schema.
Replaces the Qwen/transformers model that was in app.py.
"""

import os
import re
import json
import uuid
import urllib.parse
from typing import Optional, List, Literal, Dict
import requests
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

load_dotenv()

from llms import crew_llm_groq as crew_llm_4m  # using Groq now (others kept in llms.py for later)

# ══════════════════════════════════════════════════════════════
# Pydantic Schema
# ══════════════════════════════════════════════════════════════

class ResourceItem(BaseModel):
    title: str
    url: Optional[str] = None
    type: str = "article"  # "video" | "article" | "course" | "book" | "practice"


class QuizQuestion(BaseModel):
    question: str
    options: Dict[str, str] = Field(default_factory=dict)  # {"A": "...", "B": "...", ...}
    answer: str = "A"


class RoadmapTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: str
    duration: str
    resources: List[ResourceItem] = Field(default_factory=list)
    completed: bool = False


class RoadmapPhase(BaseModel):
    phase_number: int
    title: str
    description: str
    duration: str
    tasks: List[RoadmapTask]
    quiz: List[QuizQuestion] = Field(default_factory=list)  # per-phase MCQ quiz


class RoadmapOutput(BaseModel):
    track: str
    level: str
    goal: str
    total_duration: str
    summary: str
    display_hint: str = "timeline"  # "timeline" | "kanban" | "checklist"
    phases: List[RoadmapPhase]


# ══════════════════════════════════════════════════════════════
# Prompt builder
# ══════════════════════════════════════════════════════════════

_LEVEL_DESC = {
    "beginner":     "no prior experience in this area",
    "intermediate": "knows the basics, has some hands-on experience",
    "advanced":     "experienced practitioner wanting to deepen expertise",
}

def _build_prompt(
    track: str,
    level: str,
    goal: str,
    note: str = "",
    completed_tasks: Optional[List[str]] = None,
) -> str:
    level_desc = _LEVEL_DESC.get(level.lower(), level)

    completed_note = ""
    if completed_tasks:
        done_str = "; ".join(completed_tasks[:12])
        completed_note = (
            f"\n\nThe user has already completed these topics — build on them, "
            f"don't repeat them as primary tasks: {done_str}"
        )

    extra_note = f"\n\nExtra instruction from the user: {note}" if note.strip() else ""

    schema_example = {
        "track": track,
        "level": level,
        "goal": goal,
        "total_duration": "12 weeks",
        "summary": "A 2-sentence overview of what the learner will achieve.",
        "display_hint": "timeline",
        "phases": [
            {
                "phase_number": 1,
                "title": "Foundation",
                "description": "Build the core skills needed to get started.",
                "duration": "3 weeks",
                "tasks": [
                    {
                        "id": "p1t1",
                        "title": "Learn the basics of X",
                        "description": (
                            "Study the official documentation and work through "
                            "introductory tutorials. Focus on concepts A, B, and C."
                        ),
                        "duration": "1 week",
                        "resources": [
                            {
                                "title": "Official Documentation",
                                "url": "https://docs.example.com",
                                "type": "article",
                            },
                            {
                                "title": "Intro Tutorial on YouTube",
                                "url": "https://youtube.com",
                                "type": "video",
                            },
                        ],
                        "completed": False,
                    }
                ],
            }
        ],
    }

    schema_json = json.dumps(schema_example, indent=2, ensure_ascii=False)

    return f"""You are an expert learning path designer specializing in tech, business, and professional education.

Create a detailed, actionable personalized roadmap for:
- Track / Subject : {track}
- Current Level   : {level} — {level_desc}
- Goal            : {goal}{completed_note}{extra_note}

Rules:
1. Include 3–5 phases. Each phase must have 3–5 concrete tasks.
2. Resources should be real, free, and well-known (YouTube, Coursera free audit, official docs, freeCodeCamp, MDN, etc.).
3. Tasks must be specific actions a learner can actually do, not vague advice.
4. Durations must be realistic for the given level.
5. display_hint: use "timeline" for sequential paths (default), "kanban" if multiple tracks can be explored in parallel, "checklist" for short single-skill paths under 3 weeks total.

Return ONLY valid JSON — no markdown code fences, no commentary, nothing outside the JSON object. Follow this exact structure:

{schema_json}"""


# ══════════════════════════════════════════════════════════════
# JSON parser / validator
# ══════════════════════════════════════════════════════════════

def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _ensure_task_ids(data: dict) -> dict:
    for pi, phase in enumerate(data.get("phases", []), 1):
        for ti, task in enumerate(phase.get("tasks", []), 1):
            if not task.get("id"):
                task["id"] = f"p{pi}t{ti}"
            task.setdefault("completed", False)
            task.setdefault("resources", [])
    return data


def _fallback_roadmap(track: str, level: str, goal: str) -> RoadmapOutput:
    return RoadmapOutput(
        track=track,
        level=level,
        goal=goal,
        total_duration="Self-paced",
        summary=(
            f"A personalized learning path for {track}. "
            "Follow the phases at your own pace and adjust based on your progress."
        ),
        display_hint="timeline",
        phases=[
            RoadmapPhase(
                phase_number=1,
                title="Getting Started",
                description=f"Explore the fundamentals of {track}.",
                duration="2–3 weeks",
                tasks=[
                    RoadmapTask(
                        id="p1t1",
                        title=f"Research {track} fundamentals",
                        description=(
                            "Search for beginner guides, official documentation, "
                            "and introductory YouTube playlists."
                        ),
                        duration="1 week",
                        resources=[
                            ResourceItem(
                                title="YouTube Search",
                                url="https://www.youtube.com",
                                type="video",
                            ),
                            ResourceItem(
                                title="freeCodeCamp",
                                url="https://www.freecodecamp.org",
                                type="course",
                            ),
                        ],
                    ),
                    RoadmapTask(
                        id="p1t2",
                        title="Set up your learning environment",
                        description="Install necessary tools, create accounts, and prepare your workspace.",
                        duration="2–3 days",
                        resources=[],
                    ),
                ],
            ),
            RoadmapPhase(
                phase_number=2,
                title="Core Skills",
                description=f"Build practical skills in {track}.",
                duration="4–6 weeks",
                tasks=[
                    RoadmapTask(
                        id="p2t1",
                        title="Complete a structured course",
                        description=f"Find a well-rated course on Coursera or Udemy focused on {track}.",
                        duration="3–4 weeks",
                        resources=[
                            ResourceItem(
                                title="Coursera",
                                url="https://www.coursera.org",
                                type="course",
                            )
                        ],
                    ),
                    RoadmapTask(
                        id="p2t2",
                        title="Build a small project",
                        description="Apply what you've learned by building something tangible.",
                        duration="1–2 weeks",
                        resources=[],
                    ),
                ],
            ),
            RoadmapPhase(
                phase_number=3,
                title="Goal Achievement",
                description=f"Align your skills with your goal: {goal}.",
                duration="3–4 weeks",
                tasks=[
                    RoadmapTask(
                        id="p3t1",
                        title="Work on a portfolio-worthy project",
                        description="Build something that demonstrates your skills to potential employers or collaborators.",
                        duration="2 weeks",
                        resources=[],
                    ),
                    RoadmapTask(
                        id="p3t2",
                        title="Reflect and plan next steps",
                        description="Review what you've achieved and identify the next learning milestone.",
                        duration="2–3 days",
                        resources=[],
                    ),
                ],
            ),
        ],
    )


def _parse_output(raw: str, track: str, level: str, goal: str) -> RoadmapOutput:
    text = _strip_fences(raw)

    # Try to extract JSON object if there's surrounding text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        text = match.group(0)

    try:
        data = json.loads(text)
        data = _ensure_task_ids(data)
        return RoadmapOutput(**data)
    except Exception as exc:
        print(f"[RoadmapAgent] Parse error: {exc}\nRaw snippet: {raw[:400]}")
        return _fallback_roadmap(track, level, goal)


# ══════════════════════════════════════════════════════════════
# Enrichment: real resources (Serper) + per-phase quizzes (Groq)
# ══════════════════════════════════════════════════════════════

def _serper_search(query: str, num: int = 1) -> list:
    """Return real organic web results from Serper (or [] if unavailable)."""
    key = os.environ.get("SERPER_API_KEY", "")
    if not key:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": num},
            timeout=8,
        )
        resp.raise_for_status()
        return resp.json().get("organic", [])[:num]
    except Exception:
        return []


def _real_resources(topic: str, track: str) -> list:
    """Build a small set of REAL/guaranteed-loading resources for one topic:
    a real article (Serper), a YouTube search, and a course search."""
    q = urllib.parse.quote_plus(f"{topic} {track}".strip())
    out = []
    organic = _serper_search(f"{topic} {track} tutorial guide", 1)
    if organic:
        item = organic[0]
        link = item.get("link", "")
        if link:
            out.append({"title": (item.get("title") or "Article")[:120], "url": link, "type": "article"})
    out.append({"title": f"{topic} — video tutorials", "url": f"https://www.youtube.com/results?search_query={q}", "type": "video"})
    out.append({"title": f"{topic} — courses", "url": f"https://www.coursera.org/search?query={q}", "type": "course"})
    return out


def _attach_real_resources(data: dict, track: str) -> dict:
    """Replace each task's resources with real, verified-to-load links."""
    for phase in data.get("phases", []):
        for tk in phase.get("tasks", []):
            title = (tk.get("title") or "").strip()
            if title:
                try:
                    tk["resources"] = _real_resources(title, track)
                except Exception as exc:
                    print(f"[RoadmapAgent] resource error for '{title}': {exc}")
    return data


def _groq_client():
    try:
        from groq import Groq
        key = os.environ.get("GROQ_API_KEY", "")
        return Groq(api_key=key) if key else None
    except Exception:
        return None


def _attach_phase_quizzes(data: dict, track: str) -> dict:
    """Generate a short MCQ quiz for each phase (Groq JSON mode)."""
    client = _groq_client()
    if client is None:
        return data
    for phase in data.get("phases", []):
        topics = ", ".join(t.get("title", "") for t in phase.get("tasks", []))[:400]
        title = phase.get("title", "")
        prompt = (
            f'Create exactly 4 multiple-choice questions to test a learner AFTER completing the phase '
            f'"{title}" in the field "{track}". Topics covered in this phase: {topics}.\n'
            "Each question has 4 options (A, B, C, D) and exactly one correct answer.\n"
            'Return ONLY valid JSON: {"questions":[{"question":"...","options":'
            '{"A":"...","B":"...","C":"...","D":"..."},"answer":"A"}]}'
        )
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert quiz creator. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1600,
                response_format={"type": "json_object"},
            )
            qs = json.loads(resp.choices[0].message.content).get("questions", [])
            phase["quiz"] = qs[:5]
        except Exception as exc:
            print(f"[RoadmapAgent] phase quiz error for '{title}': {exc}")
            phase["quiz"] = []
    return data


def _enrich_roadmap(roadmap: RoadmapOutput, track: str) -> RoadmapOutput:
    """Best-effort: add real resources + per-phase quizzes. Never raises."""
    try:
        data = roadmap.model_dump()
        data = _attach_real_resources(data, track)
        data = _attach_phase_quizzes(data, track)
        return RoadmapOutput(**data)
    except Exception as exc:
        print(f"[RoadmapAgent] enrichment error: {exc}")
        return roadmap


# ══════════════════════════════════════════════════════════════
# Main generation function
# ══════════════════════════════════════════════════════════════

def generate_roadmap(
    track: str,
    level: str,
    goal: str,
    note: str = "",
    completed_tasks: Optional[List[str]] = None,
) -> RoadmapOutput:
    """
    Generate a structured learning roadmap using a CrewAI agent.
    Returns a validated RoadmapOutput (never raises — falls back gracefully).
    """
    prompt = _build_prompt(track, level, goal, note, completed_tasks)

    planner = Agent(
        role="Expert Learning Path Designer",
        goal="Create a structured, actionable, personalized learning roadmap as valid JSON.",
        backstory=(
            "You are a seasoned educational technologist and curriculum designer "
            "with expertise across tech, business, and professional development. "
            "You always output clean, valid JSON following the exact schema provided."
        ),
        llm=crew_llm_4m,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )

    task = Task(
        description=prompt,
        expected_output=(
            "A valid JSON object representing the learning roadmap. "
            "No markdown, no text outside the JSON."
        ),
        agent=planner,
    )

    crew = Crew(
        agents=[planner],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        result = crew.kickoff()
        roadmap = _parse_output(result.raw, track, level, goal)
    except Exception as exc:
        print(f"[RoadmapAgent] Generation error: {exc}")
        roadmap = _fallback_roadmap(track, level, goal)

    # Merge-in real resources + per-phase quizzes (best-effort)
    return _enrich_roadmap(roadmap, track)


def refresh_roadmap(stored_roadmap: dict, track: str, level: str, goal: str) -> RoadmapOutput:
    """
    Regenerate a roadmap taking the user's completed tasks into account.
    Used for the monthly refresh feature.
    """
    completed_tasks = []
    for phase in stored_roadmap.get("phases", []):
        for task in phase.get("tasks", []):
            if task.get("completed"):
                completed_tasks.append(task.get("title", ""))

    return generate_roadmap(
        track=track,
        level=level,
        goal=goal,
        note="Build on the user's progress. Adjust remaining tasks and suggest advanced next steps.",
        completed_tasks=completed_tasks if completed_tasks else None,
    )
