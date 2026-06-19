"""
Career / Track Comparison Tool — Phase 4 core logic.
Exports consumed by app.py:
    llm                  — LLM instance for the agent
    LANG_CONFIG          — Language-specific prompts, criteria labels
    search_web           — SERPER web-search tool instance
    create_comparator_agent — Factory → CrewAI Agent
"""

import os
from dotenv import load_dotenv
from crewai import Agent
from crewai_tools import SerperDevTool

load_dotenv()

# Web search + comparison needs reliable native tool-calling → gpt-4.1-mini
# (flash-lite returns empty responses with CrewAI tool calls)
from llms import crew_llm_4m as llm

# SERPER search tool (requires SERPER_API_KEY in .env)
search_web = SerperDevTool(
    api_key=os.environ.get("SERPER_API_KEY", ""),
    n_results=5,
)

# ---------------------------------------------------------------------------
# Language configuration
# ---------------------------------------------------------------------------
LANG_CONFIG = {
    "en": {
        "criteria": {
            "1": "Required Skills",
            "2": "Average Salary",
            "3": "Learning Duration",
            "4": "Market Demand",
            "5": "Difficulty Level",
            "6": "Job Opportunities",
            "7": "Alternative Paths",
        },
        "task_prompt": (
            "Search the web for the most recent available information about these tracks/careers: {tracks}\n\n"
            "Context: Location={location}, Currency={currency}. Reference year: {year} "
            "(use the latest data you can find — recent figures are perfectly fine as estimates for this year).\n"
            "Compare them on: {criteria}\n\n"
            "For EACH criterion and EACH track provide:\n"
            "  - The actual data/value (give your best estimate from recent data — NEVER refuse or leave blank)\n"
            "  - A source URL where this info was found\n\n"
            "IMPORTANT: You must always produce the comparison. If exact current-year data is unavailable, "
            "use the most recent figures and note them as estimates. Do not apologize or decline.\n\n"
            "Return ONLY valid JSON — no markdown, no preamble:\n"
            "{{\n"
            '  "tracks": ["track1", "track2"],\n'
            '  "comparison": {{\n'
            '    "Criterion Name": {{\n'
            '      "track1": {{"value": "...", "source": "https://..."}},\n'
            '      "track2": {{"value": "...", "source": "https://..."}}\n'
            "    }}\n"
            "  }},\n"
            '  "insights": {{\n'
            '    "highest_salary": "track name",\n'
            '    "fastest_growing": "track name",\n'
            '    "easiest_to_start": "track name",\n'
            '    "summary": "2-3 sentence overall summary"\n'
            "  }}\n"
            "}}"
        ),
        "expected_output": (
            "Valid JSON comparing the requested tracks, with a source URL "
            "for each data point and an insights summary."
        ),
    },
    "ar": {
        "criteria": {
            "1": "المهارات المطلوبة",
            "2": "متوسط الراتب",
            "3": "مدة التعلم",
            "4": "الطلب في السوق",
            "5": "مستوى الصعوبة",
            "6": "فرص العمل",
            "7": "المسارات البديلة",
        },
        "task_prompt": (
            "ابحث على الإنترنت عن أحدث المعلومات المتاحة عن هذه المسارات/الوظائف: {tracks}\n\n"
            "السياق: الموقع={location}، العملة={currency}. السنة المرجعية: {year} "
            "(استخدم أحدث بيانات تجدها — الأرقام الحديثة مقبولة تماماً كتقديرات لهذه السنة).\n"
            "قارنها على أساس: {criteria}\n\n"
            "لكل معيار ولكل مسار قدّم:\n"
            "  - القيمة الفعلية (أعطِ أفضل تقدير من البيانات الحديثة — لا ترفض أبداً ولا تترك فراغاً)\n"
            "  - رابط المصدر الذي وجدت فيه المعلومة\n\n"
            "مهم: يجب دائماً إنتاج المقارنة. إذا لم تتوفر بيانات دقيقة للسنة الحالية، "
            "استخدم أحدث الأرقام المتاحة واعتبرها تقديرات. لا تعتذر ولا ترفض.\n\n"
            "أرجع فقط JSON صالح — بدون markdown أو مقدمة:\n"
            "{{\n"
            '  "tracks": ["مسار1", "مسار2"],\n'
            '  "comparison": {{\n'
            '    "اسم المعيار": {{\n'
            '      "مسار1": {{"value": "...", "source": "https://..."}},\n'
            '      "مسار2": {{"value": "...", "source": "https://..."}}\n'
            "    }}\n"
            "  }},\n"
            '  "insights": {{\n'
            '    "highest_salary": "اسم المسار",\n'
            '    "fastest_growing": "اسم المسار",\n'
            '    "easiest_to_start": "اسم المسار",\n'
            '    "summary": "ملخص 2-3 جمل"\n'
            "  }}\n"
            "}}"
        ),
        "expected_output": (
            "JSON صالح يقارن المسارات المطلوبة مع رابط مصدر لكل نقطة بيانات وملخص insights."
        ),
    },
}


def create_comparator_agent(lang: str = "en") -> Agent:
    """Return a CrewAI Agent configured for the given language."""
    is_ar = lang == "ar"
    return Agent(
        role="Career Research Analyst" if not is_ar else "محلل أبحاث مهني",
        goal=(
            "Research and compare career tracks using live web search, "
            "providing accurate, sourced data in structured JSON."
            if not is_ar
            else
            "البحث ومقارنة المسارات المهنية عبر الويب وإرجاع بيانات دقيقة بمصادر في JSON منظّم."
        ),
        backstory=(
            "You are an expert career analyst with deep knowledge of global job markets. "
            "You always cite sources and never invent data."
            if not is_ar
            else
            "أنت محلل مهني خبير. تستشهد دائماً بالمصادر ولا تخترع بيانات."
        ),
        tools=[search_web],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
