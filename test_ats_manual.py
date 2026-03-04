"""Manual test script for the ATS Optimizer Agent."""
import asyncio
from agents.ats_optimizer import ATSOptimizerAgent

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
    agent = ATSOptimizerAgent()
    graph = agent.build_graph().compile()

    initial_state = {
        "request_id": "manual-test-001",
        "resume_data": sample_resume,
        "job_description": sample_job_description,
        "keyword_set": {},
        "match_analysis": {},
        "optimized_sections": [],
        "optimized_resume": {},
        "ats_score": 0.0,
        "score_breakdown": {},
        "status": "pending",
        "error": None,
    }

    print("Running ATS Optimizer Agent...")
    result = await graph.ainvoke(initial_state)

    print(f"\n=== Status: {result['status']} ===")
    if result.get("error"):
        print(f"Error: {result['error']}")
        return

    print(f"\nATS Score: {result['ats_score']}/100")

    print("\nScore Breakdown:")
    for category, details in result["score_breakdown"].items():
        print(
            f"  {category}: {details['matched']}/{details['total']} "
            f"({details['rate'] * 100:.1f}%)"
        )

    print(f"\nKeywords extracted: {result['keyword_set']}")
    print(f"\nMissing keywords: {result['match_analysis'].get('missing_keywords', [])}")

    if result.get("optimized_sections"):
        print("\nOptimized Sections:")
        for section in result["optimized_sections"]:
            print(f"\n  [{section['section_name']}]")
            print(f"  Changes: {section['changes_summary']}")
            print(f"  Keywords added: {section['keywords_incorporated']}")


asyncio.run(main())
