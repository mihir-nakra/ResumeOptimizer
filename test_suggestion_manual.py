"""Manual test script for the Suggestion Generator Agent."""
import asyncio
import json

from agents.suggestion_generator import SuggestionGeneratorAgent

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
    agent = SuggestionGeneratorAgent()
    graph = agent.build_graph().compile()

    initial_state = {
        "request_id": "manual-test-001",
        "resume_data": sample_resume,
        "job_description": sample_job_description,
        "gap_analysis": {},
        "suggestions": [],
        "priority_areas": [],
        "status": "pending",
        "error": None,
    }

    print("Running Suggestion Generator Agent...")
    result = await graph.ainvoke(initial_state)

    print(f"\n=== Status: {result['status']} ===")
    if result.get("error"):
        print(f"Error: {result['error']}")
        return

    # Gap analysis
    gap_analysis = result.get("gap_analysis", {})
    gaps = gap_analysis.get("gaps", [])
    strengths = gap_analysis.get("strengths", [])
    alignment = gap_analysis.get("overall_alignment", 0.0)

    print(f"\n--- Gap Analysis (alignment: {alignment:.0%}) ---")

    if strengths:
        print(f"\nStrengths ({len(strengths)}):")
        for s in strengths:
            print(f"  + {s}")

    if gaps:
        print(f"\nGaps ({len(gaps)}):")
        for gap in gaps:
            severity = gap.get("severity", "medium").upper()
            category = gap.get("category", "unknown")
            desc = gap.get("description", "")
            req = gap.get("job_requirement", "")
            print(f"  [{severity}] ({category}) {desc}")
            if req:
                print(f"         Requirement: {req}")

    # Suggestions
    suggestions = result.get("suggestions", [])
    print(f"\n--- Suggestions ({len(suggestions)}) ---")
    for i, s in enumerate(suggestions, 1):
        impact = s.get("impact", "medium").upper()
        section = s.get("section", "general")
        suggestion = s.get("suggestion", "")
        example = s.get("example", "")
        gap_addressed = s.get("gap_addressed", "")

        print(f"\n  {i}. [{impact}] ({section}) {suggestion}")
        if gap_addressed:
            print(f"     Addresses: {gap_addressed}")
        if example:
            print(f"     Example: {example}")

    # Priority areas
    priority_areas = result.get("priority_areas", [])
    if priority_areas:
        print(f"\n--- Priority Areas ({len(priority_areas)}) ---")
        for i, area in enumerate(priority_areas, 1):
            print(f"  {i}. {area}")

    # Full JSON dump
    print("\n--- Full JSON ---")
    print(json.dumps(result, indent=2, default=str))


asyncio.run(main())
