"""Manual test script for the Interview Generator Agent."""
import asyncio
import json

from agents.interview_generator import InterviewGeneratorAgent

sample_resume = {
    "summary": "Experienced software engineer with 5 years in backend development.",
    "experience": [
        {
            "title": "Senior Developer",
            "company": "Tech Corp",
            "dates": "2020-2023",
            "bullets": [
                "Built REST APIs using Python and Flask",
                "Managed PostgreSQL databases with 10M+ rows",
                "Deployed services on AWS EC2 and S3",
            ],
        }
    ],
    "skills": ["Python", "Flask", "PostgreSQL", "AWS", "Git", "Linux"],
    "education": "B.S. Computer Science, State University, 2018",
}

sample_job_description = """
Senior Software Engineer

Requirements:
- 5+ years of experience in Python
- Experience with cloud platforms (AWS, GCP, or Azure)
- Strong understanding of microservices architecture
- Knowledge of Kubernetes and Docker
- Experience with CI/CD pipelines
- Familiarity with NoSQL databases (MongoDB, DynamoDB)
- Strong communication and collaboration skills
- Bachelor's degree in Computer Science or related field
"""


async def main():
    agent = InterviewGeneratorAgent()
    graph = agent.build_graph().compile()

    initial_state = {
        "request_id": "manual-test-001",
        "resume_data": sample_resume,
        "job_description": sample_job_description,
        "requirements": {},
        "technical_questions": [],
        "behavioral_questions": [],
        "questions": [],
        "candidate_strengths_to_probe": [],
        "potential_gaps_to_assess": [],
        "difficulty_levels": {},
        "status": "pending",
        "error": None,
    }

    print("Running Interview Generator Agent...")
    result = await graph.ainvoke(initial_state)

    print(f"\n=== Status: {result['status']} ===")
    if result.get("error"):
        print(f"Error: {result['error']}")
        return

    # Requirements
    requirements = result.get("requirements", {})
    if requirements:
        print(f"\n--- Extracted Requirements ---")
        print(f"  Role: {requirements.get('role_title', 'N/A')}")
        print(f"  Seniority: {requirements.get('seniority_level', 'N/A')}")
        print(f"  Technical skills: {', '.join(requirements.get('technical_skills', []))}")
        print(f"  Soft skills: {', '.join(requirements.get('soft_skills', []))}")
        print(f"  Experience areas: {', '.join(requirements.get('experience_areas', []))}")
        if requirements.get("responsibilities"):
            print("  Responsibilities:")
            for r in requirements["responsibilities"]:
                print(f"    - {r}")

    # Difficulty breakdown
    difficulty_levels = result.get("difficulty_levels", {})
    if difficulty_levels:
        print(f"\n--- Difficulty Breakdown ---")
        for level, count in difficulty_levels.items():
            print(f"  {level}: {count}")

    # Questions
    questions = result.get("questions", [])
    print(f"\n--- Interview Questions ({len(questions)}) ---")
    for i, q in enumerate(questions, 1):
        category = q.get("category", "unknown").upper()
        difficulty = q.get("difficulty", "medium")
        skill = q.get("skill_assessed", "")
        question_text = q.get("question", "")
        follow_ups = q.get("follow_ups", [])
        look_for = q.get("what_to_look_for", "")

        print(f"\n  {i}. [{category}] ({difficulty}) {question_text}")
        if skill:
            print(f"     Skill assessed: {skill}")
        if look_for:
            print(f"     Look for: {look_for}")
        if follow_ups:
            print(f"     Follow-ups:")
            for fu in follow_ups:
                print(f"       - {fu}")

    # Candidate insights
    strengths = result.get("candidate_strengths_to_probe", [])
    if strengths:
        print(f"\n--- Candidate Strengths to Probe ({len(strengths)}) ---")
        for i, s in enumerate(strengths, 1):
            print(f"  {i}. {s}")

    gaps = result.get("potential_gaps_to_assess", [])
    if gaps:
        print(f"\n--- Potential Gaps to Assess ({len(gaps)}) ---")
        for i, g in enumerate(gaps, 1):
            print(f"  {i}. {g}")

    # Full JSON dump
    print("\n--- Full JSON ---")
    print(json.dumps(result, indent=2, default=str))


asyncio.run(main())
