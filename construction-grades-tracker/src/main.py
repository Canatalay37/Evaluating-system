# filepath: construction-grades-tracker/construction-grades-tracker/src/main.py

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

class Student:
    def __init__(self, name, student_id):
        self.name = name
        self.student_id = student_id

def main():
    tracker = GradeTracker()
    students = {}

    while True:
        print("1. Add Student")
        print("2. Add Grade")
        print("3. Update Grade")
        print("4. View Grades")
        print("5. Exit")
        choice = input("Choose an option: ")

        if choice == '1':
            name = input("Enter student name: ")
            student_id = input("Enter student ID: ")
            students[student_id] = Student(name, student_id)
            print(f"Student {name} added.")

        elif choice == '2':
            student_id = input("Enter student ID: ")
            grade = float(input("Enter grade: "))
            tracker.add_grade(student_id, grade)
            print(f"Grade {grade} added for student ID {student_id}.")

        elif choice == '3':
            student_id = input("Enter student ID: ")
            index = int(input("Enter grade index to update: "))
            new_grade = float(input("Enter new grade: "))
            tracker.update_grade(student_id, index, new_grade)
            print(f"Grade updated for student ID {student_id}.")

        elif choice == '4':
            student_id = input("Enter student ID: ")
            grades = tracker.get_grades(student_id)
            print(f"Grades for student ID {student_id}: {grades}")

        elif choice == '5':
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()