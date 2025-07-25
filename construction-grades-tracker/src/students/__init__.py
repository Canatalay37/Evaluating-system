class Student:
    def __init__(self, student_id, name):
        self.student_id = student_id
        self.name = name

    def get_info(self):
        return {
            "id": self.student_id,
            "name": self.name
        }