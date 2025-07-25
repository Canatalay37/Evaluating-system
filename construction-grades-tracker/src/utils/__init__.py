def validate_grade(grade):
    if not (0 <= grade <= 100):
        raise ValueError("Grade must be between 0 and 100.")
    return True

def format_student_info(student):
    return f"Student ID: {student.id}, Name: {student.name}"