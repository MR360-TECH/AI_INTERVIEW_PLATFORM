"""
Generate 10 interview questions per company and write to questions.json.
Uses gemini-flash-lite-latest — one API call per company (11 total).
"""
import os, json, time, re
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client  = genai.Client(api_key=api_key)
MODEL   = "gemini-flash-lite-latest"
OUT     = os.path.join(os.path.dirname(__file__), "questions.json")

# ── company metadata (kept from original questions.json) ──────────────────────
COMPANIES = {
    "google":     {"name": "Google",     "color": "#4285F4",
                   "desc": "Google interviews emphasize algorithmic efficiency, data structures, system design at scale, and distributed systems."},
    "microsoft":  {"name": "Microsoft",  "color": "#F25022",
                   "desc": "Microsoft focuses on data structures, OS fundamentals, object-oriented design, and customer-obsessed engineering."},
    "amazon":     {"name": "Amazon",     "color": "#FF9900",
                   "desc": "Amazon candidates must demonstrate the 16 Leadership Principles alongside strong algorithmic fundamentals."},
    "meta":       {"name": "Meta",       "color": "#0668E1",
                   "desc": "Meta interviews focus on quick coding, social graph algorithms, caching strategies, and large-scale systems."},
    "netflix":    {"name": "Netflix",    "color": "#E50914",
                   "desc": "Netflix values high-performance streaming design, CDN strategies, and the Freedom & Responsibility culture."},
    "tcs":        {"name": "TCS",        "color": "#1A5A96",
                   "desc": "TCS exams assess aptitude, fundamental data structures, C/Java basics, and general reasoning."},
    "infosys":    {"name": "Infosys",    "color": "#007CC3",
                   "desc": "Infosys assessments target algorithmic coding, logical reasoning, and basic Java/Python programming."},
    "wipro":      {"name": "Wipro",      "color": "#341C75",
                   "desc": "Wipro Elite NLTH tests foundational coding, OOP concepts, and basic data structures."},
    "accenture":  {"name": "Accenture",  "color": "#A100FF",
                   "desc": "Accenture assessments cover coding, logical reasoning, pseudo-code execution, and critical thinking."},
    "cognizant":  {"name": "Cognizant",  "color": "#1282B2",
                   "desc": "Cognizant tests focus on core Java, database queries, analytical reasoning, and communication skills."},
    "capgemini":  {"name": "Capgemini",  "color": "#003189",
                   "desc": "Capgemini's GAME assessments cover pseudocode, essay writing, behavioral aptitude, and basic programming."},
}

PROMPT_TEMPLATE = """
You are a senior software engineer creating interview prep content for a platform similar to PrepInsta.

Generate exactly 10 important interview questions for **{company_name}**.
The questions should be split across 3 categories:
- "Coding & Data Structures": 4 questions  
- "System Design": 3 questions  
- "Behavioral": 3 questions  

Return ONLY a valid JSON array (no markdown, no explanation) with exactly 10 objects.
Each object must follow this exact schema:
{{
  "category": "Coding & Data Structures" | "System Design" | "Behavioral",
  "title": "Short question title",
  "difficulty": "Easy" | "Medium" | "Hard",
  "tags": ["tag1", "tag2"],
  "frequency": "High" | "Medium" | "Low",
  "question": "Full question description (2-3 sentences)",
  "answer": "Concise but thorough answer / approach explanation (3-5 sentences)",
  "python_solution": "Python code string or empty string",
  "java_solution": "Java code string or empty string",
  "cpp_solution": "C++ code string or empty string"
}}

Rules:
- Coding questions MUST have python_solution, java_solution, cpp_solution as actual working code strings.
- System Design and Behavioral questions have empty strings for solution fields.
- Questions must be specifically relevant to {company_name} interviews (real questions asked there).
- Make questions varied in difficulty and topic.
- JSON must be parseable — escape newlines in code as \\n.
"""

def build_company_json(company_key, meta, questions_list):
    """Convert flat questions list into the nested category structure."""
    cats = {}
    for q in questions_list:
        cat = q.get("category", "Coding & Data Structures")
        if cat not in cats:
            cats[cat] = []
        entry = {
            "title":      q.get("title", ""),
            "difficulty": q.get("difficulty", "Medium"),
            "tags":       q.get("tags", []),
            "frequency":  q.get("frequency", "Medium"),
            "question":   q.get("question", ""),
            "answer":     q.get("answer", ""),
            "solutions":  {
                "python": q.get("python_solution", ""),
                "java":   q.get("java_solution", ""),
                "cpp":    q.get("cpp_solution", ""),
            }
        }
        cats[cat].append(entry)

    return {
        "name":        meta["name"],
        "color":       meta["color"],
        "description": meta["desc"],
        "categories":  [
            {"title": title, "questions": qs}
            for title, qs in cats.items()
        ]
    }

def extract_json(text):
    """Pull JSON array from the model response even if there's extra text."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip markdown fences
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    # Find the array
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None

def main():
    result = {}
    total  = len(COMPANIES)

    for idx, (key, meta) in enumerate(COMPANIES.items(), start=1):
        print(f"[{idx}/{total}] Generating questions for {meta['name']}...")
        prompt = PROMPT_TEMPLATE.format(company_name=meta["name"])

        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                )
                raw = response.text
                questions = extract_json(raw)
                if questions and isinstance(questions, list) and len(questions) >= 8:
                    result[key] = build_company_json(key, meta, questions)
                    print(f"  [OK] Got {len(questions)} questions for {meta['name']}")
                    break
                else:
                    print(f"  [BAD] Bad JSON on attempt {attempt+1}, retrying...")
                    time.sleep(5)
            except Exception as e:
                print(f"  [ERR] Error on attempt {attempt+1}: {e}")
                time.sleep(10)
        else:
            print(f"  [SKIP] Skipping {meta['name']} after 3 failed attempts.")
            result[key] = build_company_json(key, meta, [])

        # Save after every company so partial progress is safe
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"  [SAVED] questions.json updated")

        # Respect rate limit: 15 RPM → 4s between calls (safe margin)
        if idx < total:
            time.sleep(5)

    print(f"\n[DONE] All {total} companies written to questions.json")

if __name__ == "__main__":
    main()
