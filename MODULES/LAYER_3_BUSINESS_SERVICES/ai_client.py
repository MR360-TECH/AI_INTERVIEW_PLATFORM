import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from google import genai
from google.genai import errors, types
from MODULES.LAYER_1_CORE_INFRASTRUCTURE.config import GEMINI_API_KEY, MODEL_NAME

# ══════════════════════════════════════════════════════════════════════════════
# RELIABLE GEMINI ACCESS
#   * every call has a hard time limit (a hung call used to block a worker until gunicorn killed it -> HTTP 500)
#   * transient failures (429 rate limit, 5xx, timeouts) are retried with a short backoff
#   * optional extras, all off unless configured in the environment:
#       GEMINI_BACKUP_KEYS       comma-separated keys from OTHER Google projects (separate free-tier quota)
#       GEMINI_FALLBACK_MODELS   comma-separated backup models tried only if MODEL_NAME keeps failing
#   MODEL_NAME itself is untouched and always tried first.
# ══════════════════════════════════════════════════════════════════════════════

TRANSIENT_CODES = (408, 429, 500, 502, 503, 504)
DEFAULT_FALLBACK_MODELS = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"   # set GEMINI_FALLBACK_MODELS="" to disable

_clients = {}
# Calls run on this pool so the request thread can stop waiting after per_call_timeout_s. The Gemini server
# refuses deadlines under 10 s, so a stuck call is left to expire by itself while we move on to the next model.
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="gemini")
SERVER_MIN_TIMEOUT_S = 10.0


class AIUnavailable(Exception):
    """Raised when no configured model/key produced usable text within the time budget."""


def _api_keys():
    keys = [os.environ.get("GEMINI_API_KEY", "").strip()]
    keys += [k.strip() for k in os.environ.get("GEMINI_BACKUP_KEYS", "").split(",")]
    seen, ordered = set(), []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def _get_clients():
    clients = []
    for key in _api_keys():
        if key not in _clients:
            _clients[key] = genai.Client(api_key=key)
        clients.append(_clients[key])
    return clients


def get_ai_client():
    """First configured client (kept for compatibility); None when no API key is set."""
    clients = _get_clients()
    return clients[0] if clients else None


def _model_chain():
    # Lite models only: bigger "flash" models spend the small token cap on hidden thinking and return empty text.
    configured = os.environ.get("GEMINI_FALLBACK_MODELS")
    if configured is None:
        configured = DEFAULT_FALLBACK_MODELS
    extra = [m.strip() for m in configured.split(",") if m.strip()]
    return [MODEL_NAME] + [m for m in extra if m != MODEL_NAME]


def _is_transient(error):
    if isinstance(error, errors.APIError):
        return error.code in TRANSIENT_CODES
    name = type(error).__name__
    return isinstance(error, (TimeoutError, FutureTimeout, ConnectionError)) or any(w in name for w in ("Timeout", "Connect", "RemoteProtocol"))


def _response_text(response):
    try:
        if response.text:
            return response.text.strip()
    except Exception:
        pass
    try:
        parts = response.candidates[0].content.parts
        return "".join(p.text for p in parts if getattr(p, "text", None)).strip()
    except Exception:
        return ""


def _was_truncated(response):
    try:
        return "MAX_TOKENS" in str(response.candidates[0].finish_reason)
    except Exception:
        return False


def _trim_to_sentence(text):
    """A reply cut off by the token limit: drop a half-written [TYPE: ..] tag and any unfinished sentence."""
    text = re.sub(r"\s*\[TYPE:?[^\]]*$", "", text).strip()
    if re.search(r"\[TYPE:\s*[A-Za-z]+\]\s*$", text):
        return text
    cut = max(text.rfind("?"), text.rfind("."), text.rfind("!"))
    return text[:cut + 1].strip() if cut >= 20 else text


def generate_text(contents, *, max_output_tokens, temperature, system_instruction=None,
                  deadline_s=20.0, per_call_timeout_s=6.0, trim_truncated=True):
    """Returns non-empty model text, or raises AIUnavailable once the time budget is used up."""
    clients = _get_clients()
    if not clients:
        raise AIUnavailable("no Gemini API key configured")

    started = time.monotonic()
    combos = [(model, index) for model in _model_chain() for index in range(len(clients))]
    last_error = "unknown"

    for round_number in range(3):
        retry_worthwhile = False
        for model, client_index in combos:
            remaining = deadline_s - (time.monotonic() - started)
            if remaining < 1.5:
                raise AIUnavailable(f"time budget used up ({last_error})")
            wait_s = min(per_call_timeout_s, remaining)
            config = types.GenerateContentConfig(
                temperature=temperature, max_output_tokens=max_output_tokens,
                system_instruction=system_instruction,
                http_options=types.HttpOptions(timeout=int(max(wait_s, SERVER_MIN_TIMEOUT_S) * 1000)))
            try:
                future = _pool.submit(clients[client_index].models.generate_content,
                                      model=model, contents=contents, config=config)
                try:
                    response = future.result(timeout=wait_s)
                except FutureTimeout:
                    raise TimeoutError(f"no reply within {wait_s:.0f}s")
                text = _response_text(response)
                if text:
                    return _trim_to_sentence(text) if (trim_truncated and _was_truncated(response)) else text
                last_error = "empty reply"
                retry_worthwhile = True
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)[:120]}"
                retry_worthwhile = retry_worthwhile or _is_transient(e)
                print(f"[GEMINI] {model} key#{client_index + 1} -> {last_error}")
        if not retry_worthwhile:
            break
        pause = 0.7 * (2 ** round_number)
        if deadline_s - (time.monotonic() - started) < pause + 1.5:
            break
        time.sleep(pause)
    raise AIUnavailable(last_error)


# Used only when the AI cannot produce a question in time. Rotated so the candidate never sees a repeat.
FALLBACK_QUESTIONS = [
    "Walk me through a challenging problem you solved recently and how you approached it.",
    "Describe a project you are proud of and the part you personally built.",
    "How do you track down a bug when you are not sure where the problem is?",
    "Tell me about a time you had to learn a new tool or concept quickly.",
    "What trade-offs do you consider when choosing between two possible solutions?",
    "How do you make sure the work you deliver is correct and easy to maintain?",
    "Describe a mistake you made on a project and what you learned from it.",
    "Which areas of your field do you want to strengthen next, and how are you working on them?",
]


def pick_fallback_question(history):
    asked = {(entry.get("text") or "").strip().lower() for entry in (history or []) if entry.get("role") == "question"}
    for question in FALLBACK_QUESTIONS:
        if question.lower() not in asked:
            return question + " [TYPE: TEXT]"
    return FALLBACK_QUESTIONS[0] + " [TYPE: TEXT]"


def trim_history_for_prompt(history, keep_first=2, keep_last=10, max_chars=700):
    """Keeps the opening exchange (it names the domain) plus the most recent turns, and caps very long answers,
    so the prompt - and the response time - stays flat however long the interview runs."""
    entries = list(history or [])
    if len(entries) > keep_first + keep_last:
        entries = entries[:keep_first] + entries[-keep_last:]
    return [{**entry, "text": (entry.get("text") or "")[:max_chars]} for entry in entries]


def attachment_analysis_failed(analysis_text):
    """True when analyze_attachment() returned one of its 'Could not analyze...' fallback messages."""
    return not analysis_text or analysis_text.startswith("Could not analyze")


def analyze_attachment(file_bytes, mime_type, context_hint=""):
    try:
        if not _api_keys():
            return "Could not analyze the attached file (Gemini API not configured)."
        prompt = "Analyze this file in the context of a job interview. " + context_hint + " Be factual and concise, 2-4 sentences only."
        return generate_text(
            [types.Part.from_bytes(data=file_bytes, mime_type=mime_type), prompt],
            max_output_tokens=600, temperature=0.2, deadline_s=45.0, per_call_timeout_s=25.0, trim_truncated=False)
    except Exception as e:
        print(f"[ATTACHMENT ANALYSIS ERROR] {e}")
        return "Could not analyze the attached file."


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_initial_question_prompt(practice_mode, practice_topic="General", lang_target="English", lang_focus="conversation", lang_level="intermediate"):
    if practice_mode == "viva":
        return (
            f"You are an academic external examiner starting a Viva Voce exam on the subject: {practice_topic}. "
            "Briefly introduce the exam and ask the candidate your very first conceptual question about this subject. "
            "Output ONLY the question text followed by [TYPE: TEXT] at the end. No preamble, no intro."
        )
    elif practice_mode == "lang":
        target_lang = lang_target or "English"
        focus_cat = lang_focus or "conversation"
        level = lang_level or "intermediate"
        is_english_target = target_lang.strip().lower() == "english"
        translation_rule_q1 = (
            ""
            if is_english_target
            else f"Format the question STRICTLY as follows: first write the question in {target_lang}, then on the very next line write the English translation in brackets like this: [English: <translation here>]. Do NOT skip the English translation. "
        )
        return (
            f"You are a language validator and native tutor. First, analyze the string: '{target_lang}'. "
            "Is this a legitimate language name (e.g. English, French, Spanish, Hindi, Telugu, Sindhi, Japanese, Arabic, Russian, etc.)? "
            "If it is NOT a legitimate or real language, respond with exactly: "
            "'ERROR: Language not found. Please start a new session and specify a valid language. [TYPE: TEXT]' "
            "If it IS a legitimate language, start a language speaking practice session. "
            f"The target language is: {target_lang}. The candidate's level is: {level.capitalize()}. "
            f"The focus category is: {focus_cat.capitalize()}. "
            "Briefly introduce the session with a warm and slightly friendly tone, then ask the first practice question or prompt. "
            f"{translation_rule_q1}"
            "The user can answer in any language they prefer. "
            "Output ONLY the formatted question followed by [TYPE: TEXT] at the end. No preamble, no extra commentary."
        )
    elif practice_mode == "drill":
        return (
            f"You are a friendly mentor starting a concept drill session on the topic: {practice_topic}. "
            "State the topic and ask the candidate their first open conceptual question. "
            "Output ONLY the question text followed by [TYPE: TEXT] at the end. No preamble, no intro."
        )
    return ""


def build_subsequent_question_prompt(practice_mode, practice_topic, lang_target, lang_focus, lang_level, difficulty, q_count, min_questions, conversation_text):
    if practice_mode == "viva":
        difficulty_instruction = (
            f"The candidate is undergoing an Academic Viva Voce exam on: {practice_topic}. "
            "Keep questions clear, technical, and strictly focused on academic course concepts. "
            "Evaluate their understanding of theory, equations, algorithms, or definitions."
        )
    elif practice_mode == "lang":
        target_lang = lang_target or "English"
        focus_cat = lang_focus or "conversation"
        level = lang_level or "intermediate"
        is_english_target = target_lang.strip().lower() == "english"
        translation_rule = (
            ""
            if is_english_target
            else f"IMPORTANT FORMAT RULE: Always write each question first in {target_lang}, then on the very next line write the English translation in brackets like this: [English: <translation here>]. Never skip the English translation. "
        )
        difficulty_instruction = (
            f"This is a FluentFlow language practice session in {target_lang}. The candidate's level is {level.capitalize()}. "
            f"Focus Category: {focus_cat.capitalize()}. "
            "Maintain a warm, polite, and professional but encouraging tone. Keep any conversational remarks extremely short (under 2 sentences). "
            "If the candidate's last response contained any clear grammatical, vocabulary, or structural mistakes, "
            "provide a single, polite, direct correction sentence (e.g., 'Correction: Instead of ..., it is better to say ...'), then immediately ask the next question. "
            f"{translation_rule}"
            "The candidate can answer in any language they prefer — do not restrict or comment on the language of their answer."
        )
    elif practice_mode == "drill":
        difficulty_instruction = (
            f"The candidate is doing a Concept Drill on: {practice_topic}. "
            "Ask helpful conceptual questions that challenge their logic and reasoning on this topic."
        )
    else:
        if difficulty == "student":
            difficulty_instruction = (
                "The candidate is a Student/Beginner. Keep questions friendly and focus on fundamental concepts. "
                "Ask practical, interview-style questions suitable for a junior role, rather than overly simplistic dictionary definitions (e.g. do not ask 'What is a computer?') and explore all categories of questions within the domain. "
                "Do NOT ask highly complex technical questions. If they answer incorrectly or struggle, change the topic and ask different question within the same domain. "
                "Do not end early unless you have asked at least 5 questions.ask mostly fundamental and basic questions for this level and only advance on recieving quality answers. "
                "Keep conversational feedback minimal and professional."
            )
        elif difficulty == "senior":
            difficulty_instruction = (
                "The candidate is a Senior/Expert. Ask challenging, deep architectural or practical scenarios. "
                "Challenge their decisions, drill down into technical specifics, and maintain a high bar. Explore different categories of questions within the domain and output only question and not anything else. Do not offer any conversational filler or praise."
            )
        else:
            difficulty_instruction = (
                "The candidate is Mid-Level. Ask standard industry questions with moderate depth and practical scenarios. "
                "Adjust difficulty adaptively based on their performance. Explore different categories of questions within the domain and output only the question. Keep feedback professional and minimal."
            )

    completion_option = ""
    if q_count >= min_questions:
        completion_option = f"If you have gathered enough evaluation data after {min_questions} questions, you may conclude by outputting ONLY: [END_INTERVIEW]\n"

    prompt = (
        "You are an expert interviewer conducting a real-time assessment.\n\n"
        f"CANDIDATE TARGET LEVEL:\n{difficulty_instruction}\n\n"
        "CRITICAL DOMAIN RULE:\n"
        "Determine the candidate's core domain/role from their first answer. You MUST stay strictly 100% within this domain. Never switch to unrelated fields.\n\n"
        "RULES FOR OUTPUT:\n"
        "1. Output ONLY the raw next question. Keep it concise (under 2 sentences). ZERO preamble, conversational filler, praise, or acknowledgment.\n"
        "2. If they struggle or answer 'I don't know', DO NOT give them the answer. Change the topic/concept/context within the domain and output the next question immediately.\n"
        "3. Explore diverse categories of questions within the domain without repeating topics.\n"
        "4. HUMAN INTERVIEWER CLARIFICATION RULE: If the candidate indicates they do not understand a term or question, briefly clarify (in 1 short sentence), then state the question.\n"
        "5. BEHAVIORAL RULE: You may seamlessly integrate 1-2 behavioral or situational questions (e.g., 'Tell me about yourself', 'Why should we hire you?', or domain conflict scenarios).\n"
        "6. INPUT TAG RULE: You MUST append a tag at the very end of your output:\n"
        "   - `[TYPE: CODE]` if they need to write or fix code.\n"
        "   - `[TYPE: FILE]` if they need to upload a diagram or image.\n"
        "   - `[TYPE: TEXT]` for all standard conceptual questions.\n"
        f"{completion_option}\n"
        f"Conversation so far:\n{conversation_text}\n"
        "Output ONLY the raw question text with its tag below:"
    )
    return prompt


def build_ajax_system_prompt(domain, difficulty, resume_summary, is_practice, submit_q_count, min_questions, max_questions):
    if difficulty == "student":
        diff_note = "Candidate level: Student/Beginner. Ask practical beginner-friendly questions. No advanced or architecture-level questions."
    elif difficulty == "senior":
        diff_note = "Candidate level: Senior/Expert. Ask deep technical, architectural, and scenario-based questions. Maintain a high bar."
    else:
        diff_note = "Candidate level: Mid-Level. Ask standard industry questions with moderate depth."

    prompt_parts = [
        f"You are a strict {domain} interviewer. Domain: {domain}. {diff_note}",
        f"Resume summary: {resume_summary}" if resume_summary else "",
        f"CRITICAL RULE: ALL questions MUST be strictly within the '{domain}' domain only. NEVER ask questions from unrelated fields.",
        "Output ONLY the raw next question. Explore diverse categories within the domain. Change topic if the previous answer was wrong. Keep it concise (1-2 sentences). ZERO preamble, filler, or acknowledgment.",
        "If they answer 'I don't know', DO NOT give them the answer. Just output the next question immediately.",
    ]
    if not is_practice:
        prompt_parts.append(
            "BEHAVIORAL/SITUATIONAL RULE: Ensure to ask 2 behavioral or situational questions "
            "(e.g., 'Tell me about yourself', 'Why should we hire you?', or domain scenario questions) randomly or near the end before concluding."
        )

    if not is_practice and submit_q_count >= min_questions:
        prompt_parts.append("If the candidate has demonstrated sufficient knowledge and you are ready to finish the interview, output ONLY the exact phrase: [END_INTERVIEW]")

    prompt_parts.append(f"Question {submit_q_count + 1} (Max: {max_questions}). You MUST append [TYPE: TEXT], [TYPE: CODE], or [TYPE: FILE] at the end.")

    return " ".join(p for p in prompt_parts if p)


def build_evaluation_prompt(practice_mode, practice_topic, lang_target, difficulty, domain_val, conversation_text):
    if practice_mode == "viva":
        grading_instruction = f"Academic Viva Voce exam on {practice_topic}. Grade strictly on theoretical accuracy, equation mastery, and academic definitions."
    elif practice_mode == "lang":
        grading_instruction = f"Language practice in {lang_target or 'English'}. Grade on grammar, vocabulary, pronunciation cues, and conversational fluency."
    elif practice_mode == "drill":
        grading_instruction = f"Concept Drill on {practice_topic}. Grade on conceptual understanding, depth of knowledge, and logical reasoning."
    else:
        if difficulty == "student":
            grading_instruction = "Candidate level: Student/Beginner. Grade encouragingly on fundamentals, problem-solving potential, and core understanding."
        elif difficulty == "senior":
            grading_instruction = "Candidate level: Senior/Expert. Grade strictly on deep technical proficiency, system architecture, performance, and best practices."
        else:
            grading_instruction = "Candidate level: Mid-Level. Grade balanced on standard industry expectations and practical domain skills."

    prompt = (
        f"Evaluate this {domain_val} interview assessment thoroughly based on the candidate's transcript.\n"
        f"{grading_instruction}\n\n"
        "Format your output EXACTLY as follows:\n"
        "SCORE: [number from 1.0 to 10.0]\n"
        "SUMMARY:\n"
        "[Paragraph 1: An overall assessment of candidate performance, domain knowledge, and problem-solving approach during the interview.]\n\n"
        "[Paragraph 2: A detailed technical critique discussing key answers provided, depth of conceptual understanding demonstrated, and notable gaps or inaccuracies observed.]\n\n"
        "[Paragraph 3: A constructive evaluation offering practical guidance, areas to strengthen, and a professional recommendation regarding domain readiness.]\n\n"
        "CRITICAL FORMATTING RULES:\n"
        "1. Do NOT use any section labels, headers, or markdown titles (such as 'Strengths:', 'Weaknesses:', 'Overview:', '###', 'Key Strengths', etc.).\n"
        "2. Do NOT use bullet points or numbered lists.\n"
        "3. Write the evaluation strictly as 3-4 distinct, detailed, and professional paragraphs separated by blank lines.\n\n"
        f"Transcript:\n{conversation_text}"
    )
    return prompt
