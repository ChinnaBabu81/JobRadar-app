"""
Resume Tailor — Uses Claude AI to generate job-specific tailored resumes
"""

import os
import anthropic
import logging

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TAILOR_SYSTEM_PROMPT = """You are an expert resume writer and career coach specializing in AI, 
data science, and tech internship roles. Your task is to tailor a candidate's base resume 
to perfectly match a specific job description.

Rules:
1. Keep ALL real experience, education, and skills from the base resume — do not fabricate anything
2. Reorder bullet points to highlight the most relevant experience for THIS job first
3. Adjust wording of existing bullet points to match keywords from the job description
4. Add a targeted professional summary at the top specific to this role
5. Highlight the most relevant technical skills prominently
6. Return a clean, ATS-friendly formatted resume in Markdown
7. Keep it concise — 1 page equivalent
8. Use action verbs that match the job's language
"""


def tailor_resume(base_resume: str, job_title: str, company: str, job_description: str) -> dict:
    """
    Generate a tailored resume for a specific job using Claude.
    
    Args:
        base_resume: The candidate's base resume text
        job_title: The job title
        company: The company name
        job_description: The full job description
    
    Returns:
        dict with 'resume' (markdown), 'tips' (list of tailoring tips), 'match_score' (0-100)
    """
    prompt = f"""
Please tailor the following resume for this specific job opportunity.

## TARGET JOB
**Title:** {job_title}
**Company:** {company}

## JOB DESCRIPTION
{job_description[:3000]}

## BASE RESUME
{base_resume[:3000]}

## YOUR TASK
1. Generate a tailored resume in Markdown format
2. List 3-5 specific tailoring tips you applied
3. Estimate a match score (0-100) based on how well the resume aligns with the job

Respond in this exact JSON format:
{{
  "tailored_resume": "... full markdown resume ...",
  "tips": ["tip1", "tip2", "tip3"],
  "match_score": 85,
  "key_keywords_matched": ["keyword1", "keyword2"],
  "missing_skills": ["skill1", "skill2"]
}}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=TAILOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        if raw.endswith("```"):
            raw = raw[:-3]

        import json
        result = json.loads(raw.strip())
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Resume tailoring failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "tailored_resume": base_resume,
                "tips": ["Could not tailor resume — check your API key"],
                "match_score": 0,
                "key_keywords_matched": [],
                "missing_skills": []
            }
        }


def analyze_job_fit(base_resume: str, job_description: str) -> dict:
    """Quick job fit analysis without full resume rewrite."""
    prompt = f"""
Analyze how well this resume matches the job description.

RESUME:
{base_resume[:2000]}

JOB DESCRIPTION:
{job_description[:2000]}

Return JSON:
{{
  "match_score": 75,
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "recommendation": "Apply / Maybe Apply / Skip"
}}
"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        import json
        return json.loads(raw.strip())
    except Exception as e:
        return {"match_score": 0, "strengths": [], "gaps": [], "recommendation": "Unknown"}
