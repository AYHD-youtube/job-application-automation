# ai_scorer.py
"""AI-powered job relevance scoring using Google Gemini"""
import json
import re
import google.generativeai as genai
from typing import Dict, Any


def configure_gemini(api_key: str):
    """Configure Gemini API"""
    genai.configure(api_key=api_key)


def score_job_relevance(
    job_data: Dict[str, Any],
    resume_text: str,
    api_key: str
) -> Dict[str, Any]:
    """
    Score job relevance using AI
    
    Args:
        job_data: Normalized job data
        resume_text: Candidate's resume text
        api_key: Google API key for Gemini
        
    Returns:
        Scoring data with score, reasoning, matches, etc.
    """
    configure_gemini(api_key)
    
    prompt = f"""You are an expert career counselor analyzing job-candidate match.

Job Title: {job_data.get('Title', 'N/A')}
Company: {job_data.get('Company', 'N/A')}
Location: {job_data.get('Location', 'N/A')}
Description: {job_data.get('Description', 'N/A')}

Candidate Resume:
{resume_text}

Score the match from 0-100 based on:
- Technical skills match (43%): How well do the candidate's technical skills align with job requirements?
- Experience level (35%): Does the candidate have appropriate years and type of experience?
- Domain relevance (15%): Is the candidate's background in a relevant industry/domain?
- Location fit (2%): Is relocation required? Remote work compatibility?
- Additional qualifications (5%): Certifications, education, soft skills

Provide a detailed analysis and return ONLY valid JSON:
{{
  "score": <number 0-100>,
  "reasoning": "<2-3 sentences explaining the score>",
  "key_matches": ["<matching skill 1>", "<matching skill 2>", "<matching skill 3>"],
  "missing_skills": ["<missing skill 1>", "<missing skill 2>"],
  "recommendation": "<APPLY if score >= 60, otherwise SKIP>"
}}"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Parse the response
        output_text = response.text.strip()
        
        # Remove markdown formatting if present
        output_text = re.sub(r'```json\n?|```\n?', '', output_text).strip()
        
        # Parse JSON
        scoring_data = json.loads(output_text)
        
        # Validate and normalize
        score = int(scoring_data.get('score', 0))
        scoring_data['score'] = score
        
        if not scoring_data.get('recommendation'):
            scoring_data['recommendation'] = 'APPLY' if score >= 60 else 'SKIP'
        
        if not isinstance(scoring_data.get('key_matches'), list):
            scoring_data['key_matches'] = []
        
        if not isinstance(scoring_data.get('missing_skills'), list):
            scoring_data['missing_skills'] = []
        
        return scoring_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing AI response: {e}")
        print(f"Response text: {output_text}")
        
        # Fallback: try to extract score with regex
        score_match = re.search(r'"?score"?\s*:\s*(\d+)', output_text)
        score = int(score_match.group(1)) if score_match else 0
        
        return {
            'score': score,
            'reasoning': 'Failed to parse AI response',
            'recommendation': 'APPLY' if score >= 60 else 'SKIP',
            'key_matches': [],
            'missing_skills': []
        }
        
    except Exception as e:
        print(f"Error scoring job with AI: {e}")
        return {
            'score': 0,
            'reasoning': f'Error: {str(e)}',
            'recommendation': 'SKIP',
            'key_matches': [],
            'missing_skills': []
        }


def generate_cover_letter(
    job_data: Dict[str, Any],
    resume_text: str,
    scoring_data: Dict[str, Any],
    api_key: str,
    resume_url: str,
    custom_prompt: str = None,
    attach_resume: bool = True
) -> str:
    """
    Generate personalized cover letter using AI
    
    Args:
        job_data: Normalized job data
        resume_text: Candidate's resume text
        scoring_data: AI scoring results
        api_key: Google API key for Gemini
        resume_url: URL to resume
        custom_prompt: Custom prompt template (optional)
        attach_resume: Whether resume will be attached to email (default: True)
        
    Returns:
        Generated cover letter in HTML format
    """
    configure_gemini(api_key)
    
    key_matches = ', '.join(scoring_data.get('key_matches', []))
    missing_skills = ', '.join(scoring_data.get('missing_skills', []))
    
    # Use custom prompt if provided, otherwise use default
    if custom_prompt and custom_prompt.strip():
        # Replace placeholders in custom prompt
        prompt = custom_prompt.format(
            job_title=job_data.get('Title', 'N/A'),
            company=job_data.get('Company', 'N/A'),
            description=job_data.get('Description', 'N/A'),
            resume=resume_text,
            score=scoring_data.get('score', 0),
            key_matches=key_matches,
            missing_skills=missing_skills,
            reasoning=scoring_data.get('reasoning', ''),
            location=job_data.get('Location', 'N/A')
        )
    else:
        # Default prompt
        prompt = f"""Write a compelling, personalized cover letter that emphasizes the candidate's matching skills.

**SCORING INSIGHTS:**
Relevance Score: {scoring_data.get('score', 0)}/100
Key Strengths: {key_matches}
Areas to Address: {missing_skills}
Reasoning: {scoring_data.get('reasoning', '')}

**JOB DETAILS:**
Title: {job_data.get('Title', 'N/A')}
Company: {job_data.get('Company', 'N/A')}
Location: {job_data.get('Location', 'N/A')}
Description: {job_data.get('Description', 'N/A')}

**CANDIDATE RESUME:**
{resume_text}

**INSTRUCTIONS:**
1. Start with ONLY ONE greeting: "Dear {job_data.get('Company', 'Hiring Team')} Hiring Team," (use the actual company name from job_data)
2. Write 3-4 paragraphs emphasizing the key matching skills ({key_matches})
3. Provide specific examples of achievements
4. If any missing skills are trainable, express enthusiasm to learn
5. Close with "Regards," followed by the candidate's name
6. DO NOT add any resume links or job URLs in the body - they will be added automatically

**FORMAT:**
- Start with single greeting line: "Dear [ACTUAL_COMPANY_NAME] Hiring Team,"
- 1-2 body paragraphs (150 - 200 words)
- End with "Regards," and candidate name
- Professional but personable tone
- No placeholders or brackets
- HTML format with <p> tags
- DO NOT include resume or job links in the letter body"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        cover_letter = response.text.strip()
        
        # Ensure it's in HTML format
        if not cover_letter.startswith('<'):
            # Wrap paragraphs in <p> tags
            paragraphs = cover_letter.split('\n\n')
            cover_letter = '\n'.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())
        
        # Add professional footer based on resume attachment setting
        if attach_resume:
            footer = f"""
<p><br></p>
<p><em>I have attached my resume for your review. I look forward to discussing this opportunity further.</em></p>"""
        else:
            footer = f"""
<p><br></p>
<p><em>I look forward to discussing this opportunity further.</em></p>"""
        
        cover_letter = cover_letter + footer
        
        return cover_letter
        
    except Exception as e:
        print(f"Error generating cover letter: {e}")
        return f"<p>Error generating cover letter: {str(e)}</p>"


def extract_company_domain(company_name: str, api_key: str) -> str:
    """
    Extract company domain using AI
    
    Args:
        company_name: Company name
        api_key: Google API key for Gemini
        
    Returns:
        Company domain (e.g., 'example.com') or 'UNKNOWN'
    """
    configure_gemini(api_key)
    
    prompt = f"""Extract the company domain from: {company_name}

Return ONLY the domain in format: example.com
- No https:// or www.
- If company name contains spaces, try to guess the domain
- If completely unknown, return: UNKNOWN

Examples:
- Google → google.com
- Meta Platforms → meta.com
- JPMorgan Chase → jpmorganchase.com"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        domain = response.text.strip()
        
        # Clean up the response
        domain = domain.replace('https://', '').replace('http://', '').replace('www.', '')
        domain = domain.split('/')[0]  # Remove any path
        domain = domain.strip()
        
        return domain if domain else 'UNKNOWN'
        
    except Exception as e:
        print(f"Error extracting domain: {e}")
        return 'UNKNOWN'

