#!/usr/bin/env python3
"""
Add demo grades to existing submissions for testing the Grade Distribution chart
"""
import os
import sys
from models.database import db
from models.entities import Submission, Grade
from config import Config
from flask import Flask

# Create Flask app context
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    # Get all submissions without grades
    submissions = Submission.query.filter(Submission.grade == None).all()
    print(f"Found {len(submissions)} submissions without grades")
    
    if not submissions:
        print("All submissions already have grades!")
        sys.exit(0)
    
    # Add demo grades
    for i, sub in enumerate(submissions):
        # Create varied scores for demo
        if i % 3 == 0:
            score = 85  # High
            feedback = "Excellent work! Clear writing with good vocabulary usage."
        elif i % 3 == 1:
            score = 65  # Mid
            feedback = "Good effort. Some grammar improvements needed."
        else:
            score = 45  # Low
            feedback = "Needs more work. Focus on grammar and sentence structure."
        
        grade = Grade(
            submission_id=sub.id,
            score=score,
            grammar_feedback="Work on verb tenses and subject-verb agreement",
            vocabulary_feedback="Use more diverse vocabulary",
            general_feedback=feedback,
            instructor_approved=True
        )
        db.session.add(grade)
        print(f"Added grade {score}% to submission {sub.id}")
    
    db.session.commit()
    print(f"\nSuccessfully added {len(submissions)} demo grades!")
