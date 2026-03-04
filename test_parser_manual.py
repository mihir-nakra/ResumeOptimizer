"""Manual test script for the Resume Parser Agent."""
import asyncio
import json
import os

from agents.resume_parser import ResumeParserAgent

RESUME_PATH = os.path.join(os.path.dirname(__file__), "resume.pdf")


async def main():
    agent = ResumeParserAgent()
    graph = agent.build_graph().compile()

    initial_state = {
        "request_id": "manual-test-001",
        "file_path": RESUME_PATH,
        "file_type": "pdf",
        "raw_text": "",
        "structured_data": {},
        "status": "pending",
        "error": None,
    }

    print(f"Parsing resume: {RESUME_PATH}")
    print("Running Resume Parser Agent...\n")
    result = await graph.ainvoke(initial_state)

    print(f"=== Status: {result['status']} ===")
    if result.get("error"):
        print(f"Error: {result['error']}")
        return

    # Raw text preview
    raw = result.get("raw_text", "")
    print(f"\n--- Raw Text ({len(raw)} chars) ---")
    print(raw[:500])
    if len(raw) > 500:
        print(f"  ... ({len(raw) - 500} more chars)")

    # Structured data
    data = result.get("structured_data", {})
    print("\n--- Structured Data ---")

    contact = data.get("contact_info", {})
    print(f"\nContact: {contact.get('name', 'N/A')}")
    print(f"  Email:    {contact.get('email', 'N/A')}")
    print(f"  Phone:    {contact.get('phone', 'N/A')}")
    print(f"  Location: {contact.get('location', 'N/A')}")
    print(f"  LinkedIn: {contact.get('linkedin', 'N/A')}")

    if data.get("summary"):
        print(f"\nSummary: {data['summary'][:200]}")

    if data.get("experience"):
        print(f"\nExperience ({len(data['experience'])} entries):")
        for exp in data["experience"]:
            print(f"  - {exp['title']} at {exp['company']} ({exp.get('start_date', '?')} - {exp.get('end_date', '?')})")
            for bullet in exp.get("description", [])[:3]:
                print(f"      * {bullet}")

    if data.get("education"):
        print(f"\nEducation ({len(data['education'])} entries):")
        for edu in data["education"]:
            print(f"  - {edu['degree']} — {edu['institution']}")

    if data.get("skills"):
        print(f"\nSkills ({len(data['skills'])}): {', '.join(data['skills'])}")

    if data.get("certifications"):
        print(f"\nCertifications: {', '.join(data['certifications'])}")

    if data.get("projects"):
        print(f"\nProjects ({len(data['projects'])} entries):")
        for proj in data["projects"]:
            print(f"  - {proj['name']}: {proj.get('description', '')[:100]}")

    # Dump full JSON for inspection
    print("\n--- Full JSON ---")
    print(json.dumps(data, indent=2))


asyncio.run(main())
