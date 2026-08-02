import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Check for API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment or .env file.")
    exit(1)

client = genai.Client(api_key=api_key)

# Load existing questions.json
questions_path = "questions.json"
if os.path.exists(questions_path):
    with open(questions_path, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    print("Error: questions.json not found in the current directory.")
    exit(1)

# List of companies to verify and populate
companies = list(data.keys())

for company_key in companies:
    company = data[company_key]
    # Count current questions
    total_qs = 0
    for cat in company["categories"]:
        total_qs += len(cat["questions"])
    
    print(f"Company: {company['name']} currently has {total_qs} questions.")
    
    if total_qs >= 15:
        print(f"Skipping {company['name']} as it already has 15 or more questions.")
        continue
    
    needed = 15 - total_qs
    print(f"Generating {needed} more questions for {company['name']}...")
    
    # Prompt Gemini to generate structured JSON representing the additional questions
    prompt = f"""
You are an expert technical interviewer. We need to add exactly {needed} more high-quality interview questions for the company '{company['name']}'.
The company description is: "{company['description']}".

We currently have these categories for this company:
{json.dumps([cat['title'] for cat in company['categories']], indent=2)}

Please generate exactly {needed} new and unique interview questions distributed across these categories.
For Coding categories (e.g. 'Coding & Data Structures' or 'Coding'), you MUST provide complete and clean code implementations in python, java, and cpp inside the `solutions` field.
For non-coding categories (e.g. 'System Design', 'Behavioral', 'Aptitude & General', 'Aptitude'), the `solutions` dictionary should be empty (e.g. {{}}).

Each question MUST strictly follow this JSON schema:
{{
  "category_title": "Must match one of the existing category titles exactly",
  "title": "Clear, concise title of the question",
  "difficulty": "Easy" or "Medium" or "Hard",
  "tags": ["list", "of", "tags"],
  "frequency": "High" or "Medium",
  "question": "The complete interview question text",
  "answer": "Detailed answer overview, approach description, and explanation",
  "solutions": {{
    "python": "Code string in python (escaped for JSON)",
    "java": "Code string in java (escaped for JSON)",
    "cpp": "Code string in cpp (escaped for JSON)"
  }}
}}

Return ONLY a JSON list containing these {needed} questions. No markdown wrapper (no ```json), no extra text. Just raw JSON list.
"""
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text.strip()
        # Clean any accidental markdown backticks just in case
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
            
        new_qs = json.loads(raw_text)
        
        # Add generated questions to their respective categories
        added_count = 0
        for q in new_qs:
            cat_title = q.get("category_title")
            # Find category
            category_found = False
            for cat in company["categories"]:
                if cat["title"].lower() == cat_title.lower():
                    # Strip category_title from dict before appending
                    q_to_append = {
                        "title": q["title"],
                        "difficulty": q["difficulty"],
                        "tags": q["tags"],
                        "frequency": q["frequency"],
                        "question": q["question"],
                        "answer": q["answer"],
                        "solutions": q.get("solutions", {})
                    }
                    cat["questions"].append(q_to_append)
                    category_found = True
                    added_count += 1
                    break
            if not category_found:
                # Fallback to the first category if title mismatch
                if company["categories"]:
                    q_to_append = {
                        "title": q["title"],
                        "difficulty": q["difficulty"],
                        "tags": q["tags"],
                        "frequency": q["frequency"],
                        "question": q["question"],
                        "answer": q["answer"],
                        "solutions": q.get("solutions", {})
                    }
                    company["categories"][0]["questions"].append(q_to_append)
                    added_count += 1
                    
        print(f"Successfully added {added_count} questions to {company['name']}.")
        
        # Save progress immediately
        with open(questions_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        # Delay to prevent rate limit on free tier (limit is 15 RPM for gemini-1.5-flash)
        print("Sleeping 12 seconds to prevent rate limit...")
        time.sleep(12)
        
    except Exception as e:
        print(f"Error generating questions for {company['name']}: {e}")
        print("Sleeping 15 seconds before retry...")
        time.sleep(15)

print("All questions generated and saved to questions.json successfully!")

