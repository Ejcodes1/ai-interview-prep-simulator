"""Curated lexicon of role/skill terms used by FR-06 keyword extraction.

This is a plain, dependency-free lookup table (no LLM/NLP model involved —
that is deliberate, see `parser.extract_skills`). It covers common technical
skills, tools, and soft skills likely to appear across resumes and job
descriptions so a straightforward substring/word-boundary match reliably
finds several matches in realistic input.
"""
from __future__ import annotations

# Canonical display form of each recognized skill/term. Matching is done
# case-insensitively against these phrases.
SKILLS_LEXICON: list[str] = [
    # Programming languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "SQL", "R", "Scala",
    # Web / frameworks
    "Flask", "Django", "React", "Angular", "Vue", "Node.js", "Express",
    "Spring", "HTML", "CSS", "REST API", "GraphQL",
    # Data / ML
    "Machine Learning", "Deep Learning", "Data Analysis", "Pandas", "NumPy",
    "TensorFlow", "PyTorch", "Data Visualization", "ETL", "Data Modeling",
    # Cloud / DevOps
    "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "CI/CD",
    "Jenkins", "Terraform", "Linux", "Git", "GitHub",
    # Databases
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",
    # Testing / QA
    "Unit Testing", "pytest", "Test Automation", "Debugging",
    # Product / process
    "Agile", "Scrum", "Kanban", "Project Management", "Requirements Analysis",
    "System Design", "Software Architecture", "API Integration",
    # Soft skills
    "Communication", "Leadership", "Teamwork", "Problem Solving",
    "Critical Thinking", "Time Management", "Collaboration", "Mentoring",
    "Presentation", "Stakeholder Management", "Attention to Detail",
    "Adaptability", "Customer Service", "Negotiation",
]
