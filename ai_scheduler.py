"""
ai_scheduler.py — The core AI scheduling engine for SleepWell.

Flow:
1. Receives user profile + list of tasks for the day
2. Optionally parses free-text / speech input into structured tasks
3. Calls Claude API to generate an optimized, sleep-safe schedule
4. Returns structured schedule blocks ready to save to DB
"""

import os
import json
import re
from typing import List, Optional
from datetime import datetime, date
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def parse_free_text_tasks(free_text: str, user_context: dict) -> list:
    """
    Use Claude to parse natural language / speech-to-text input into structured tasks.
    e.g. "finish the report by 5pm, gym for an hour, cook dinner" 
         → [{title: "Finish report", estimated_minutes: 60, deadline: "17:00", priority: "urgent"}, ...]
    """
    prompt = f"""Parse the following text into a JSON array of tasks. 
Each task must have: title, estimated_minutes (integer), priority ("urgent"/"normal"/"flexible"), task_type ("work"/"study"/"personal"/"health"), and optionally deadline_time ("HH:MM" 24h format if mentioned).

Rules:
- Be generous with time estimates (add ~20% buffer)
- If no time is mentioned, estimate based on task type
- Deadlines: "by 5pm" → "17:00", "tonight" → use bedtime {user_context.get('bedtime_target', '23:00')}
- If something sounds health/exercise related, set task_type to "health"
- Respond ONLY with valid JSON array, no other text

Input text: "{free_text}"
"""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def generate_schedule(
    user_profile: dict,
    tasks: list,
    target_date: str,
    free_text: Optional[str] = None
) -> dict:
    """
    Main scheduling function. Calls Claude to produce an optimized daily schedule.

    user_profile: {
        sleep_goal_hours, bedtime_target, wake_time_target, stress_level, name
    }
    tasks: list of task dicts with title, estimated_minutes, priority, task_type, deadline
    target_date: "YYYY-MM-DD"
    free_text: optional raw text to also include as extra tasks

    Returns: {
        blocks: [...],
        ai_notes: str,
        confidence: int (0-100),
        warnings: [str]
    }
    """

    # If there's free text input, parse it first and merge into tasks
    extra_tasks = []
    if free_text and free_text.strip():
        extra_tasks = parse_free_text_tasks(free_text, user_profile)

    all_tasks = tasks + extra_tasks

    bedtime   = user_profile.get("bedtime_target", "23:00")
    wake_time = user_profile.get("wake_time_target", "07:00")
    stress    = user_profile.get("stress_level", "moderate")
    sleep_hrs = user_profile.get("sleep_goal_hours", 8.0)
    name      = user_profile.get("name", "the user")

    tasks_json = json.dumps(all_tasks, indent=2)

    system_prompt = """You are SleepWell's AI scheduler. Your job is to create a realistic, 
stress-reducing daily schedule that ALWAYS protects sleep time. You are like a calm, 
supportive coach who helps people be productive without burning out.

Core rules you MUST follow:
1. Sleep block is ALWAYS locked and cannot be moved
2. Add a 30-minute "Wind Down" block before bedtime (no screens, calming activities)
3. Schedule urgent tasks in peak energy hours (morning 9-11am, afternoon 2-4pm)
4. Add 10-15 min buffers between task blocks
5. Never schedule more than 90 min of focused work without a break
6. If tasks don't fit before bedtime, mark overflow tasks and explain
7. Add meals as breaks if the schedule is long (breakfast ~8am, lunch ~12-1pm, dinner ~6-7pm)
8. Flexible tasks go in lower-energy afternoon slots
9. Health/exercise tasks go in morning if possible
10. Always respond with ONLY valid JSON, no other text"""

    user_prompt = f"""Create a daily schedule for {name} on {target_date}.

User profile:
- Wake time: {wake_time}
- Bedtime target: {bedtime}  
- Sleep goal: {sleep_hrs} hours
- Stress level: {stress}

Tasks to schedule:
{tasks_json}

Return a JSON object with this exact structure:
{{
  "blocks": [
    {{
      "block_type": "task|sleep|break|wind_down|buffer|meal",
      "title": "Block title",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "is_locked": false,
      "color": "red|yellow|blue|purple|green|gray",
      "task_ref": "exact task title this maps to, or null",
      "is_auto_adjusted": false
    }}
  ],
  "ai_notes": "A friendly 2-3 sentence explanation of scheduling decisions",
  "confidence": 85,
  "warnings": ["list of any issues, e.g. tasks that couldn't fit"],
  "overflow_tasks": ["tasks that couldn't fit before sleep"]
}}

Color guide: red=urgent, yellow=normal, blue=flexible, purple=sleep/wind-down, green=health/breaks, gray=buffer/meal
Sleep block MUST be from {bedtime} to {wake_time} next day and is_locked=true.
Wind Down block at {_subtract_minutes(bedtime, 30)} to {bedtime} and is_locked=true."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return a minimal safe schedule if parsing fails
        result = _fallback_schedule(bedtime, wake_time, tasks)

    # Attach parsed free-text tasks for the router to save
    result["parsed_extra_tasks"] = extra_tasks
    return result


def _subtract_minutes(time_str: str, minutes: int) -> str:
    """Helper: subtract minutes from a HH:MM string."""
    try:
        h, m = map(int, time_str.split(":"))
        total = h * 60 + m - minutes
        if total < 0:
            total += 1440
        return f"{total // 60:02d}:{total % 60:02d}"
    except Exception:
        return time_str


def _fallback_schedule(bedtime: str, wake_time: str, tasks: list) -> dict:
    """Minimal fallback schedule if AI response fails to parse."""
    wind_down = _subtract_minutes(bedtime, 30)
    blocks = [
        {
            "block_type": "wind_down",
            "title": "Wind Down 🌙",
            "start_time": wind_down,
            "end_time": bedtime,
            "is_locked": True,
            "color": "purple",
            "task_ref": None,
            "is_auto_adjusted": False
        },
        {
            "block_type": "sleep",
            "title": "Sleep 😴",
            "start_time": bedtime,
            "end_time": wake_time,
            "is_locked": True,
            "color": "purple",
            "task_ref": None,
            "is_auto_adjusted": False
        }
    ]
    return {
        "blocks": blocks,
        "ai_notes": "Could not fully generate schedule. Sleep block is protected.",
        "confidence": 50,
        "warnings": ["Schedule generation encountered an issue. Please try again."],
        "overflow_tasks": [t.get("title", "") for t in tasks],
        "parsed_extra_tasks": []
    }
