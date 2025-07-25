class GradeTracker:
    def __init__(self):
        self.grades = {}

    def add_grade(self, student_id, grade):
        if student_id not in self.grades:
            self.grades[student_id] = []
        self.grades[student_id].append(grade)

    def update_grade(self, student_id, index, new_grade):
        if student_id in self.grades and 0 <= index < len(self.grades[student_id]):
            self.grades[student_id][index] = new_grade

    def get_grades(self, student_id):
        return self.grades.get(student_id, [])

    def get_average_grade(self, student_id):
        if student_id in self.grades and self.grades[student_id]:
            return sum(self.grades[student_id]) / len(self.grades[student_id])
        return 0.0