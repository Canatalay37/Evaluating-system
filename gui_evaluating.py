import os
from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
# import pandas as pd  # Removed for Docker compatibility
import numpy as np
import io
import openpyxl 
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Reset database on each app start for a clean run
RESET_DB_ON_START = True

# Database configuration
os.makedirs(app.instance_path, exist_ok=True)
DB_FILENAME = "evaluation_system.db"
DB_FILEPATH = os.path.join(app.instance_path, DB_FILENAME)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_FILEPATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def format_csv_cell(cell):
    if cell is None:
        return ''
    if isinstance(cell, str):
        raw = cell.strip()
        if raw and ('.' in raw or ',' in raw):
            try:
                normalized = raw.replace(',', '.')
                numeric_value = float(normalized)
                formatted = f"{numeric_value:.2f}".replace('.', ',')
                return formatted
            except ValueError:
                pass
        return f'"{cell.replace(chr(34), chr(34)+chr(34))}"'
    if isinstance(cell, (int, float, np.integer, np.floating)):
        formatted = f"{float(cell):.2f}".replace('.', ',')
        return formatted
    return str(cell)

# Database Models
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(50), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    exams = db.relationship('Exam', backref='course', lazy=True, cascade='all, delete-orphan')
    clos = db.relationship('CLO', backref='course', lazy=True, cascade='all, delete-orphan')
    students = db.relationship('Student', backref='course', lazy=True, cascade='all, delete-orphan')

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    question_count = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    students_per_exam = db.Column(db.Integer, nullable=False)
    
    # Relationships
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')

class CLO(db.Model):
    __tablename__ = 'clo'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, nullable=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_idx = db.Column(db.Integer, nullable=False)
    max_points = db.Column(db.Float, nullable=False)
    qct = db.Column(db.Float, default=0.0)
    w = db.Column(db.Float, default=0.0)
    bl = db.Column(db.Float, default=0.0)
    
    # Relationships
    clo_mappings = db.relationship('QuestionCLOMapping', backref='question', lazy=True, cascade='all, delete-orphan')
    grades = db.relationship('Grade', backref='question', lazy=True, cascade='all, delete-orphan')

class QuestionCLOMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    clo_id = db.Column(db.Integer, db.ForeignKey('clo.id'), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    grades = db.relationship('Grade', backref='student', lazy=True, cascade='all, delete-orphan')

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    grade = db.Column(db.Float, nullable=False)


# ROUTES
@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        # Get course information
        course_code = request.form["course_code"]
        teacher_name = request.form["teacher_name"]
        semester = request.form["semester"]
        
        exam_count = int(request.form["exam_count"])
        clo_count = int(request.form.get("clo_count", 10))
        clo_names = []
        for i in range(clo_count):
            clo_name = request.form.get(f"clo_name_{i}", f"CLO {i+1}")
            clo_names.append(clo_name)
        # Separate student count for each exam (list)
        students_per_exam = []
        for i in range(exam_count):
            val = request.form.get(f"students_per_exam_{i}", "0")
            try:
                students_per_exam.append(int(val))
            except ValueError:
                students_per_exam.append(0)
        # Total student count (take maximum to preserve existing logic especially for student_grades)
        student_count = max(students_per_exam) if students_per_exam else 0

        # Save form data for back navigation
        session["main_form"] = {k: v for k, v in request.form.items()}
        
        # Save to database
        course = Course(
            course_code=course_code,
            teacher_name=teacher_name,
            semester=semester
        )
        db.session.add(course)
        db.session.commit()

        # Save CLOs to database
        for i, name in enumerate(clo_names):
            clo = CLO(course_id=course.id, name=name, order=i+1)
            db.session.add(clo)
        db.session.commit()
        
        # Save course_id to session
        session["course_id"] = course.id
        session["course_code"] = course_code
        session["teacher_name"] = teacher_name
        session["semester"] = semester
        session["exam_count"] = exam_count
        session["student_count"] = student_count
        session["students_per_exam"] = students_per_exam
        session["clo_count"] = clo_count
        session["clo_names"] = clo_names
        session.pop("exams", None) 
        session.pop("question_points", None)
        session.pop("clos", None)
        session.pop("students", None)
        session.pop("clo_q_data", None)
        session.pop("clo_results", None)
        session.pop("total_clo_results", None)
        return redirect(url_for("exam_details"))
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    main_form = session.get("main_form", {})
    return render_template(
        "main.html",
        clo_count=clo_count,
        clo_names=clo_names,
        main_form=main_form,
        students_per_exam=session.get("students_per_exam", []),
    )

@app.route("/exam_details", methods=["GET", "POST"])
def exam_details():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))
    
    exam_count = session.get("exam_count", 0)
    if request.method == "POST":
        session["exam_details_form"] = {k: v for k, v in request.form.items()}
        weights = []
        for i in range(exam_count):
            weight_raw = request.form.get(f"weight_{i}", "0")
            try:
                weight_val = int(weight_raw)
            except ValueError:
                weight_val = 0
            weights.append(weight_val)

        total_weight = sum(weights)
        if total_weight != 100:
            error = f"Total exam weight is {total_weight}%. It must be exactly 100%."
            return render_template(
                "exam_details.html",
                exam_count=exam_count,
                enumerate=enumerate,
                session=session,
                error=error,
                form_data=request.form,
            )
        
        # Process exam details
        exams = []
        for i in range(exam_count):
            exam = Exam(
                course_id=course_id,
                name=request.form[f"exam_name_{i}"],
                question_count=int(request.form[f"question_count_{i}"]),
                weight=weights[i] if i < len(weights) else 0,
                students_per_exam=session["students_per_exam"][i]
            )
            db.session.add(exam)
            exams.append(exam)
        
        db.session.commit()
        
        # Update session
        session["exams"] = [{"name": e.name, "question_count": e.question_count, "weight": e.weight} for e in exams]
        
        return redirect(url_for("question_points"))

    form_data = session.get("exam_details_form")
    if not form_data and session.get("exams"):
        form_data = {}
        for i, exam in enumerate(session.get("exams", [])):
            form_data[f"exam_name_{i}"] = exam.get("name", "")
            form_data[f"question_count_{i}"] = exam.get("question_count", "")
            form_data[f"weight_{i}"] = exam.get("weight", "")
    return render_template(
        "exam_details.html",
        exam_count=exam_count,
        enumerate=enumerate,
        session=session,
        form_data=form_data,
    )

@app.route("/question_points", methods=["GET", "POST"])
def question_points():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))
    
    exams = session.get("exams", [])
    students_per_exam = session.get("students_per_exam", [])
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    question_points = session.get("question_points", [])
    
    if not exams:
        return redirect(url_for("exam_details"))
    
    if request.method == "POST":
        # Server-side validation: each exam's question points total must be 100
        question_points_list = []
        for idx, exam in enumerate(exams):
            running_sum = 0.0
            questions = []
            for q in range(int(exam["question_count"])):
                points = float(request.form.get(f"points_{idx}_{q}", 0))
                running_sum += points
                clo_keys = request.form.getlist(f"clo_{idx}_{q}")
                selected_clos = [int(c) for c in clo_keys]
                # Automatically calculate QCT value: (Question points × Exam percentage) ÷ 100
                qct = (points * exam["weight"]) / 100
                bl = float(request.form.get(f"bl_{idx}_{q}", 0))
                n_clo = len(selected_clos)
                w_val = 1.0 / n_clo if n_clo > 0 else 0.0
                
                # Save Question to database
                exam_db = Exam.query.filter_by(course_id=course_id, name=exam["name"]).first()
                if exam_db:
                    question = Question(
                        exam_id=exam_db.id,
                        question_idx=q,
                        max_points=points,
                        qct=qct,
                        bl=bl
                    )
                    db.session.add(question)
                    db.session.flush()  # ID'yi al
                    
                    # Save CLO mappings
                    for clo_idx in selected_clos:
                        clo = CLO.query.filter_by(course_id=course_id, order=clo_idx).first()
                        if clo:
                            mapping = QuestionCLOMapping(question_id=question.id, clo_id=clo.id)
                            db.session.add(mapping)
                        else:
                            # CLO bulunamadıysa log ekle
                            print(f"CLO with order {clo_idx} not found for course {course_id}")
                            # Inform user in case of error
                            return f"CLO {clo_idx} not found for course. Please check CLO configuration.", 400
                    
                    # En az bir CLO seçilmiş olmalı
                    if not selected_clos:
                        return f"Question {q+1} in {exam['name']} must have at least one CLO selected.", 400
                    
                    # QCT is now automatically calculated, so validation is not needed
                    # if qct < 0 or qct > 100:
                    #     return f"Question {q+1} in {exam['name']} QCT value must be between 0 and 100.", 400
                    
                    if bl < 1 or bl > 6:
                        return f"Question {q+1} in {exam['name']} Bloom Level must be between 1 and 6.", 400
                
                # Her CLO için ayrı kayıt oluştur
                for clo_idx in selected_clos:
                    questions.append({
                        "points": points,
                        "clo": clo_idx,  # Tek bir CLO ID
                        "qct": qct,
                        "w": w_val,
                        "bl": bl,
                        "question_idx": q
                    })
            question_points_list.append(questions)
            # Toplamı kontrol et
            if abs(running_sum - 100.0) > 1e-6:
                return f"Question points total for {exams[idx]['name']} is {running_sum}. Total must be 100.", 400
        
        db.session.commit()
        session["question_points"] = question_points_list
        return redirect(url_for("student_grades"))
    
    points_prefill = []
    bl_prefill = []
    clo_prefill = []
    for exam_idx, exam in enumerate(exams):
        q_count = int(exam["question_count"])
        points_row = [None] * q_count
        bl_row = [None] * q_count
        clo_row = [set() for _ in range(q_count)]
        if question_points and exam_idx < len(question_points):
            for rec in question_points[exam_idx]:
                q_idx = rec.get("question_idx")
                if q_idx is None or q_idx >= q_count:
                    continue
                if points_row[q_idx] is None:
                    points_row[q_idx] = rec.get("points")
                if bl_row[q_idx] is None:
                    bl_row[q_idx] = rec.get("bl")
                clo_val = rec.get("clo")
                if clo_val:
                    clo_row[q_idx].add(clo_val)
        points_prefill.append(points_row)
        bl_prefill.append(bl_row)
        clo_prefill.append([sorted(list(s)) for s in clo_row])

    return render_template(
        "question_points.html",
        exams=exams,
        clo_count=clo_count,
        clo_names=clo_names,
        students_per_exam=students_per_exam,
        enumerate=enumerate,
        session=session,
        points_prefill=points_prefill,
        bl_prefill=bl_prefill,
        clo_prefill=clo_prefill,
    )

@app.route("/student_grades", methods=["GET", "POST"])
def student_grades():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))
    
            # Get data from database
    exams_db = Exam.query.filter_by(course_id=course_id).all()
    students_db = Student.query.filter_by(course_id=course_id).all()
    
            # Get data from session (for backward compatibility)
    exams = session.get("exams", [])
    student_count = session.get("student_count")
    question_points_nested = session.get("question_points")
    students_per_exam = session.get("students_per_exam", [])
    
    if not exams or not student_count or not question_points_nested:
        return redirect(url_for("main"))
    
    all_questions_flat_for_jinja = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        for q_idx_in_exam in range(int(exam['question_count'])):
            max_points = 0
            # Sadece ilk kaydın points'ini al (birden fazla CLO olabilir)
            if question_points_nested and len(question_points_nested) > exam_idx:
                q_records = [rec for rec in question_points_nested[exam_idx] if rec.get('question_idx', q_idx_in_exam) == q_idx_in_exam]
                if q_records:
                    max_points = q_records[0]['points']
            all_questions_flat_for_jinja.append({
                'exam_idx': exam_idx,
                'question_idx_in_exam': q_idx_in_exam,
                'global_question_idx': global_q_idx_counter,
                'max_points': max_points
            })
            global_q_idx_counter += 1

    # students_data'yı session'dan al, yoksa veritabanından al
    students_data = []
    
    # Önce session'dan kontrol et
    if 'students' in session and session['students']:
        students_data = session['students']
        print(f"=== DEBUG: Using students data from session: {len(students_data)} students ===")
        # Debug: Session'daki verileri kontrol et
        for i, student in enumerate(students_data[:3]):  # İlk 3 öğrenciyi göster
            print(f"Session Öğrenci {i+1}: {student.get('name', 'N/A')} - grades = {student.get('grades', [])[:5]}...")
    elif students_db:
        print("=== DEBUG: No students data in session, checking database ===")
        # Session'da yoksa veritabanından al
        for student in students_db:
            grades = [None] * len(all_questions_flat_for_jinja)
            # Veritabanından grades'ları al - doğru mapping ile
            for grade in student.grades:
                # Question'ın exam_id ve question_idx'ini bul
                question = Question.query.get(grade.question_id)
                if question:
                    # Bu question'ın global_question_idx'ini bul
                    global_q_idx = 0
                    for exam_idx, exam in enumerate(exams_db):
                        for q_idx_in_exam in range(int(exam.question_count)):
                            if exam.id == question.exam_id and q_idx_in_exam == question.question_idx:
                                if global_q_idx < len(grades):
                                    grades[global_q_idx] = grade.grade
                                break
                            global_q_idx += 1
            
            students_data.append({
                "number": student.number,
                "name": student.name,
                "grades": grades,
                "total": sum(g for g in grades if g not in [None])
            })
        print(f"=== DEBUG: Using students data from database: {len(students_data)} students ===")
    else:
        # Hiçbiri yoksa boş liste oluştur
        for i in range(student_count):
            students_data.append({
                "number": "",
                "name": "",
                "grades": [None] * len(all_questions_flat_for_jinja),
                "total": 0.0
            })
        print(f"=== DEBUG: Creating empty students data: {len(students_data)} students ===")

    if request.method == "POST":
        # Check if this is a bloom mapping form submission
        if any(key.startswith('qct_') or key.startswith('w_') or key.startswith('spm_') or key.startswith('bl_') for key in request.form.keys()):
            # Handle bloom mapping form submission
            clo_count = session.get("clo_count", 10)
            clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
            
            # Process form data and save to session
            clo_q_data = []
            global_q_idx_counter = 0
            for clo_idx in range(1, clo_count+1):
                clo_row = {}
                global_q_idx_counter = 0
                for exam_idx, exam in enumerate(exams):
                    for q_idx_in_exam in range(int(exam['question_count'])):
                        qct = float(request.form.get(f"qct_{clo_idx-1}_{global_q_idx_counter}", 0))
                        w = float(request.form.get(f"w_{clo_idx-1}_{global_q_idx_counter}", 0))
                        spm = float(request.form.get(f"spm_{clo_idx-1}_{global_q_idx_counter}", 0))
                        bl = float(request.form.get(f"bl_{clo_idx-1}_{global_q_idx_counter}", 0))
                        
                        clo_row[global_q_idx_counter] = {
                            'qct': qct,
                            'w': w,
                            'spm': spm,
                            'bl': bl
                        }
                        global_q_idx_counter += 1
                clo_q_data.append(clo_row)
            
            session["clo_q_data"] = clo_q_data
            
            # Perform calculations
            all_questions_flat_map = []
            global_q_idx_counter = 0
            for exam_idx, exam in enumerate(exams):
                exam_map = []
                for q_idx_in_exam in range(int(exam['question_count'])):
                    exam_map.append(global_q_idx_counter)
                    global_q_idx_counter += 1
                all_questions_flat_map.append(exam_map)
            
            question_performance_medians = session.get("question_performance_medians", [])
            clo_results = []
            for clo_idx in range(1, clo_count+1):
                qct_list, w_list, spm_list, bl_list, ep_list = [], [], [], [], []
                for exam_idx, exam in enumerate(exams):
                    for q in range(exam["question_count"]):
                        global_q_idx = all_questions_flat_map[exam_idx][q]
                        qct = clo_q_data[clo_idx-1][global_q_idx]['qct']
                        w = clo_q_data[clo_idx-1][global_q_idx]['w']
                        spm = clo_q_data[clo_idx-1][global_q_idx]['spm']
                        bl = clo_q_data[clo_idx-1][global_q_idx]['bl']
                        ep_val = 0.0
                        if exam_idx < len(question_points_nested):
                            for q_rec in question_points_nested[exam_idx]:
                                if q_rec.get('question_idx') == q:
                                    ep_val = q_rec.get('points', 0)
                                    break
                        qct_list.append(qct)
                        w_list.append(w)
                        spm_list.append(spm)
                        bl_list.append(bl)
                        ep_list.append(ep_val)
                clo_results.append({
                    "max_clo_score": max_possible_clo_score(qct_list, w_list),
                    "weighted_clo_score": weighted_clo_score(qct_list, w_list, spm_list),
                    "normalized_clo_score": normalized_clo_score(qct_list, w_list, spm_list, bl_list, ep_list),
                    "weighted_bloom_score": weighted_bloom_score(qct_list, w_list, bl_list),
                    "average_bloom_score": average_bloom_score(qct_list, w_list, bl_list)
                })
            
            total_clo_results = {
                "total_max_clo_score": sum(r["max_clo_score"] for r in clo_results),
                "total_weighted_clo_score": sum(r["weighted_clo_score"] for r in clo_results),
                "total_normalized_clo_score": sum(r["normalized_clo_score"] for r in clo_results),
                "total_average_bloom_score": sum(r["average_bloom_score"] for r in clo_results),
                "total_weighted_bloom_score": sum(r["weighted_bloom_score"] for r in clo_results)
            }
            
            session["clo_results"] = clo_results
            session["total_clo_results"] = total_clo_results
            
            # Automatically update SPM values
            if 'students' in session and session['students']:
                students = session['students']
                question_performance_medians = []
                global_q_idx_counter = 0
                
                for exam_idx, exam in enumerate(exams):
                    for q_idx_in_exam in range(int(exam['question_count'])):
                        grades_for_question = []
                        for student in students:
                            if global_q_idx_counter < len(student['grades']):
                                grade_val = student['grades'][global_q_idx_counter]
                                if grade_val is None or grade_val == '':
                                    continue
                                grades_for_question.append(grade_val)
                        
                        spm_val = 0.0
                        if grades_for_question:
                            # Max points'i bul
                            max_points = 0
                            for q_rec in question_points_nested[exam_idx]:
                                if q_rec.get('question_idx') == q_idx_in_exam:
                                    max_points = q_rec.get('points', 0)
                                    break
                            
                            if max_points > 0:
                                avg_val = np.mean(grades_for_question)
                                spm_val = round((avg_val / max_points) * 100, 2)
                        
                        question_performance_medians.append(spm_val)
                        global_q_idx_counter += 1
                
                session["question_performance_medians"] = question_performance_medians
            
            return redirect(url_for("student_grades"))
        else:
            # Handle regular student grades form submission
            students = []
            total_questions_count = len(all_questions_flat_for_jinja)

            for student_idx in range(int(student_count)):
                current_student_data = students_data[student_idx] if student_idx < len(students_data) else {
                    "number": "", "name": "", "grades": [0.0] * total_questions_count, "total": 0.0
                }
                
                student_number = request.form.get(f"student_number_{student_idx}", "")
                student_name = request.form.get(f"student_name_{student_idx}", "")

                current_student_total_score = 0.0
                student_grades_list = [None] * total_questions_count 

                for q_flat in all_questions_flat_for_jinja:
                    grade_key = f"grade_{student_idx}_{q_flat['global_question_idx']}"
                    grade = request.form.get(grade_key, "")
                    try:
                        grade_value = float(grade) if grade.strip() != "" else None
                    except ValueError:
                        grade_value = None 
                    
                    # Not validasyonu - maksimum puanı aşmayı engelle
                    max_points = q_flat['max_points']
                    if grade_value is not None and grade_value > max_points:
                        grade_value = max_points
                    elif grade_value is not None and grade_value < 0:
                        grade_value = 0
                    
                    student_grades_list[q_flat['global_question_idx']] = grade_value
                    if grade_value is not None:
                        current_student_total_score += grade_value

                # Student'ı veritabanına kaydet/güncelle
                student = Student.query.filter_by(course_id=course_id, number=student_number).first()
                if not student:
                    student = Student(course_id=course_id, number=student_number, name=student_name)
                    db.session.add(student)
                    db.session.flush()
                else:
                    student.name = student_name

                # Grades'ları veritabanına kaydet/güncelle
                for q_idx, grade_value in enumerate(student_grades_list):
                    if q_idx < len(all_questions_flat_for_jinja):
                        question_global_idx = all_questions_flat_for_jinja[q_idx]['global_question_idx']
                        
                        # Son kez validasyon kontrolü
                        max_points = all_questions_flat_for_jinja[q_idx]['max_points']
                        if grade_value is not None and grade_value > max_points:
                            grade_value = max_points
                        elif grade_value is not None and grade_value < 0:
                            grade_value = 0
                        
                        # Grade'ı veritabanına kaydet/güncelle
                        existing_grade = Grade.query.filter_by(student_id=student.id, question_id=question_global_idx).first()
                        if grade_value is None:
                            # Boş bırakılanları kaydetmeyelim; varsa silmeyelim, sadece atla
                            if existing_grade:
                                pass
                        else:
                            if existing_grade:
                                existing_grade.grade = grade_value
                            else:
                                new_grade = Grade(student_id=student.id, question_id=question_global_idx, grade=grade_value)
                                db.session.add(new_grade)

                students.append({
                    "number": student_number,
                    "name": student_name,
                    "grades": student_grades_list, 
                    "total": round(current_student_total_score, 1) 
                })
            
            db.session.commit()
            session["students"] = students
            session["question_points"] = question_points_nested
            
                    # Debug: Check student data saved to session
        print("=== DEBUG: Session check after form submit ===")
        print(f"Number of students saved to session: {len(students)}")
        for i, student in enumerate(students[:3]):  # Show first 3 students
            print(f"Student {i+1}: {student['name']} - grades = {student['grades'][:5]}...")  # Show first 5 grades
        print("=== END DEBUG ===")
            
        return redirect(url_for("summary"))

    session["all_questions_flat"] = all_questions_flat_for_jinja 
    
    # Prepare bloom mapping data for the modal
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    
    # Create all_questions_flat_map for bloom mapping
    all_questions_flat_map = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        exam_map = []
        for q_idx_in_exam in range(int(exam['question_count'])):
            exam_map.append(global_q_idx_counter)
            global_q_idx_counter += 1
        all_questions_flat_map.append(exam_map)
    
    # Get or initialize bloom mapping data
    clo_q_data = session.get("clo_q_data", [])
    clo_results = session.get("clo_results", [])
    total_clo_results = session.get("total_clo_results", {})
    
    # Initialize clo_q_data if empty
    if not clo_q_data:
            clo_q_data = []
            for clo_idx in range(1, clo_count + 1):
                clo_row = {}
                global_q_idx_counter = 0
                for exam_idx, exam in enumerate(exams):
                    for q_idx_in_exam in range(int(exam['question_count'])):
                        q_clo_records = [
                            rec for rec in question_points_nested[exam_idx]
                            if rec['clo'] == clo_idx and rec.get('question_idx', q_idx_in_exam) == q_idx_in_exam
                        ]
                        
                        if q_clo_records:
                            rec = q_clo_records[0]
                            
                            # Automatically calculate SPM value
                            spm_val = 0.0
                            if 'students' in session and session['students']:
                                students = session['students']
                                grades_for_question = []
                                for student in students:
                                    if global_q_idx_counter < len(student['grades']):
                                        grade_val = student['grades'][global_q_idx_counter]
                                        if grade_val is None or grade_val == '':
                                            continue
                                        grades_for_question.append(grade_val)
                                
                                if grades_for_question:
                                    # Max points'i bul
                                    max_points = 0
                                    for q_rec in question_points_nested[exam_idx]:
                                        if q_rec.get('question_idx') == q_idx_in_exam:
                                            max_points = q_rec.get('points', 0)
                                            break
                                    
                                    if max_points > 0:
                                        avg_val = np.mean(grades_for_question)
                                        spm_val = round((avg_val / max_points) * 100, 2)
                            else:
                                # If no student data, get from question_performance_medians
                                question_performance_medians = session.get("question_performance_medians", [])
                                if global_q_idx_counter < len(question_performance_medians):
                                    spm_val = question_performance_medians[global_q_idx_counter]
                            
                            # Get QCT and W values correctly
                            qct_val = rec.get('qct', 0.0)
                            w_val = rec.get('w', 0.0)
                            bl_val = rec.get('bl', 0.0)
                            
                            clo_row[global_q_idx_counter] = {
                                'qct': qct_val,
                                'w': w_val,
                                'spm': spm_val,
                                'bl': bl_val,
                            }
                        else:
                            clo_row[global_q_idx_counter] = {
                                'qct': 0.0,
                                'w': 0.0,
                                'spm': 0.0,
                                'bl': 0.0,
                            }
                        global_q_idx_counter += 1
                clo_q_data.append(clo_row)
    
    # Calculate clo_results if empty
    if not clo_results:
        clo_results = []
        for clo_idx in range(1, clo_count+1):
            qct_list, w_list, spm_list, bl_list, ep_list = [], [], [], [], []
            for exam_idx, exam in enumerate(exams):
                for q in range(exam["question_count"]):
                    global_q_idx = all_questions_flat_map[exam_idx][q]
                    
                    # Bu CLO için bu sorunun verilerini question_points'den al
                    q_clo_records = [
                        rec for rec in question_points_nested[exam_idx]
                        if rec['clo'] == clo_idx and rec.get('question_idx', q) == q
                    ]
                    
                    if q_clo_records:
                        rec = q_clo_records[0]
                        qct = rec.get('qct', 0.0)
                        w = rec.get('w', 0.0)
                        bl = rec.get('bl', 0.0)
                        
                        # Calculate SPM value
                        spm = 0.0
                        if 'students' in session and session['students']:
                            students = session['students']
                            grades_for_question = []
                            for student in students:
                                if global_q_idx < len(student['grades']):
                                    grade_val = student['grades'][global_q_idx]
                                    if grade_val is None or grade_val == '':
                                        continue
                                    grades_for_question.append(grade_val)
                            
                            if grades_for_question:
                                max_points = rec.get('points', 0)
                                if max_points > 0:
                                    avg_val = np.mean(grades_for_question)
                                    spm = round((avg_val / max_points) * 100, 2)
                        
                        # Sadece bu CLO'ya ait olan soruları ekle
                        if qct > 0 and w > 0:
                            qct_list.append(qct)
                            w_list.append(w)
                            spm_list.append(spm)
                            bl_list.append(bl)
                            ep_list.append(rec.get('points', 0))
            
            # CLO Score hesaplamaları
            max_clo = max_possible_clo_score(qct_list, w_list)
            weighted_clo = weighted_clo_score(qct_list, w_list, spm_list)
            normalized_clo = normalized_clo_score(qct_list, w_list, spm_list, bl_list, ep_list)
            weighted_bloom = weighted_bloom_score(qct_list, w_list, bl_list)
            avg_bloom = average_bloom_score(qct_list, w_list, bl_list)
            
            clo_results.append({
                "max_clo_score": max_clo,
                "weighted_clo_score": weighted_clo,
                "normalized_clo_score": normalized_clo,
                "weighted_bloom_score": weighted_bloom,
                "average_bloom_score": avg_bloom
            })
        
        total_clo_results = {
            "total_max_clo_score": sum(r["max_clo_score"] for r in clo_results),
            "total_weighted_clo_score": sum(r["weighted_clo_score"] for r in clo_results),
            "total_normalized_clo_score": sum(r["normalized_clo_score"] for r in clo_results),
            "total_average_bloom_score": sum(r["average_bloom_score"] for r in clo_results),
            "total_weighted_bloom_score": sum(r["weighted_bloom_score"] for r in clo_results)
        }
    
    return render_template("student_grades.html", 
                            exams=exams, 
                            student_count=int(student_count),
                            question_points_nested=question_points_nested, 
                            students_data=students_data, 
                            all_questions_flat=all_questions_flat_for_jinja, 
                            students_per_exam=students_per_exam,
                            enumerate=enumerate,
                            session=session,
                            # Bloom mapping data
                            clos=list(range(1, clo_count+1)),
                            clo_names=clo_names,
                            all_questions_flat_map=all_questions_flat_map,
                            clo_q_data=clo_q_data,
                            clo_results=clo_results,
                            total_clo_results=total_clo_results)


@app.route("/bloom_mapping")
def bloom_mapping():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))

    exams = session.get("exams", [])
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    clo_results = session.get("clo_results", [])
    question_points_nested = session.get("question_points", [])
    
    if not exams:
        return redirect(url_for("student_grades"))
    
    print("=== DEBUG: bloom_mapping route started ===")
    print(f"clo_results exists: {bool(clo_results)}")
    print(f"question_points_nested exists: {bool(question_points_nested)}")
    print(f"students in session: {'students' in session}")
    
    # If clo_results doesn't exist, perform calculations
    if not clo_results and question_points_nested:
        # Create all_questions_flat_map for bloom mapping
        all_questions_flat_map = []
        global_q_idx_counter = 0
        for exam_idx, exam in enumerate(exams):
            exam_map = []
            for q_idx_in_exam in range(int(exam['question_count'])):
                exam_map.append(global_q_idx_counter)
                global_q_idx_counter += 1
            all_questions_flat_map.append(exam_map)
        
        # Initialize clo_q_data from question_points
        clo_q_data = []
        for clo_idx in range(1, clo_count + 1):
            clo_row = {}
            global_q_idx_counter = 0
            for exam_idx, exam in enumerate(exams):
                for q_idx_in_exam in range(int(exam['question_count'])):
                    # Find this question's data for this CLO
                    q_clo_records = [
                        rec for rec in question_points_nested[exam_idx]
                        if rec['clo'] == clo_idx and rec.get('question_idx', q_idx_in_exam) == q_idx_in_exam
                    ]
                    
                    if q_clo_records:
                        rec = q_clo_records[0]
                        # Automatically calculate SPM value
                        spm_val = 0.0
                        if 'students' in session and session['students']:
                            students = session['students']
                            grades_for_question = []
                            for student in students:
                                if global_q_idx_counter < len(student['grades']):
                                    grade_val = student['grades'][global_q_idx_counter]
                                    if grade_val is None or grade_val == '':
                                        continue
                                    grades_for_question.append(grade_val)
                            
                            if grades_for_question:
                                # Max points'i bul
                                max_points = 0
                                for q_rec in question_points_nested[exam_idx]:
                                    if q_rec.get('question_idx') == q_idx_in_exam:
                                        max_points = q_rec.get('points', 0)
                                        break
                                
                                if max_points > 0:
                                    avg_val = np.mean(grades_for_question)
                                    spm_val = round((avg_val / max_points) * 100, 2)
                        else:
                            # If no student data, get from question_performance_medians
                            question_performance_medians = session.get("question_performance_medians", [])
                            if global_q_idx_counter < len(question_performance_medians):
                                spm_val = question_performance_medians[global_q_idx_counter]
                        
                        # Get QCT and W values correctly
                        qct_val = rec.get('qct', 0.0)
                        w_val = rec.get('w', 0.0)
                        bl_val = rec.get('bl', 0.0)
                        
                        clo_row[global_q_idx_counter] = {
                            'qct': qct_val,
                            'w': w_val,
                            'spm': spm_val,
                            'bl': bl_val,
                        }
                    else:
                        # This question doesn't exist for this CLO, assign 0 values
                        clo_row[global_q_idx_counter] = {
                            'qct': 0.0,
                            'w': 0.0,
                            'spm': 0.0,
                            'bl': 0.0,
                        }
                    global_q_idx_counter += 1
            clo_q_data.append(clo_row)
        
        # Calculate clo_results
        clo_results = []
        for clo_idx in range(1, clo_count+1):
            qct_list, w_list, spm_list, bl_list, ep_list = [], [], [], [], []
            
            # Scan all questions for this CLO
            for exam_idx, exam in enumerate(exams):
                for q in range(exam["question_count"]):
                    global_q_idx = all_questions_flat_map[exam_idx][q]
                    
                    # Bu CLO için bu sorunun verilerini question_points'den al
                    q_clo_records = [
                        rec for rec in question_points_nested[exam_idx]
                        if rec['clo'] == clo_idx and rec.get('question_idx', q) == q
                    ]
                    
                    # Debug: CLO mapping check
                    if not q_clo_records:
                        print(f"DEBUG: CLO {clo_idx}, Exam {exam_idx}, Q{q+1}: No CLO mapping found")
                        print(f"  Available records for this exam: {[rec.get('clo') for rec in question_points_nested[exam_idx]]}")
                    else:
                        print(f"DEBUG: CLO {clo_idx}, Exam {exam_idx}, Q{q+1}: Found {len(q_clo_records)} mapping(s)")
                    
                    if q_clo_records:
                        rec = q_clo_records[0]
                        qct = rec.get('qct', 0.0)
                        w = rec.get('w', 0.0)
                        bl = rec.get('bl', 0.0)
                        
                        # Calculate SPM value - from student grades
                        spm = 0.0
                        if 'students' in session and session['students']:
                            students = session['students']
                            grades_for_question = []
                            for student in students:
                                if global_q_idx < len(student['grades']):
                                    try:
                                        grade_val = float(student['grades'][global_q_idx])
                                        grades_for_question.append(grade_val)
                                    except (ValueError, TypeError):
                                        continue
                            
                            if grades_for_question:
                                max_points = rec.get('points', 0)
                                if max_points > 0:
                                    avg_val = np.mean(grades_for_question)
                                    spm = round((avg_val / max_points) * 100, 2)
                                    print(f"CLO {clo_idx}, Q{q+1}: grades={grades_for_question}, avg={avg_val}, max_points={max_points}, SPM={spm}")
                                else:
                                    print(f"CLO {clo_idx}, Q{q+1}: max_points is 0")
                                    spm = 50.0  # Default 50% performance
                            else:
                                print(f"CLO {clo_idx}, Q{q+1}: no valid grades found")
                                spm = 50.0  # Default 50% performance
                        else:
                            print(f"CLO {clo_idx}, Q{q+1}: no students data in session")
                            spm = 50.0  # Default 50% performance
                        
                        print(f"CLO {clo_idx}, Q{q+1}: using default SPM = {spm}")
                        
                        # Sadece bu CLO'ya ait olan soruları ekle
                        if qct > 0 and w > 0:
                            qct_list.append(qct)
                            w_list.append(w)
                            spm_list.append(spm)
                            bl_list.append(bl)
                            ep_list.append(rec.get('points', 0))
                            
                            print(f"CLO {clo_idx}, Q{q+1}: QCT={qct}, W={w}, SPM={spm}, BL={bl}")
            
            # CLO Score hesaplamaları
            max_clo = max_possible_clo_score(qct_list, w_list)
            weighted_clo = weighted_clo_score(qct_list, w_list, spm_list)
            normalized_clo = normalized_clo_score(qct_list, w_list, spm_list, bl_list, ep_list)
            weighted_bloom = weighted_bloom_score(qct_list, w_list, bl_list)
            avg_bloom = average_bloom_score(qct_list, w_list, bl_list)
            
            # Debug: Eğer normalized_clo 0 ise, nedenini kontrol et
            if normalized_clo == 0:
                print(f"WARNING: CLO {clo_idx} normalized_clo is 0!")
                print(f"  qct_list: {qct_list}")
                print(f"  w_list: {w_list}")
                print(f"  spm_list: {spm_list}")
                print(f"  max_clo: {max_clo}")
                print(f"  weighted_clo: {weighted_clo}")
            
            print(f"CLO {clo_idx} Results:")
            print(f"  QCT List: {qct_list}")
            print(f"  W List: {w_list}")
            print(f"  SPM List: {spm_list}")
            print(f"  BL List: {bl_list}")
            print(f"  Max CLO: {max_clo}")
            print(f"  Weighted CLO: {weighted_clo}")
            print(f"  Normalized CLO: {normalized_clo}")
            print(f"  Weighted Bloom: {weighted_bloom}")
            print(f"  Avg Bloom: {avg_bloom}")
            
            clo_results.append({
                "max_clo_score": max_clo,
                "weighted_clo_score": weighted_clo,
                "normalized_clo_score": normalized_clo,
                "weighted_bloom_score": weighted_bloom,
                "average_bloom_score": avg_bloom
            })
        
        total_clo_results = {
            "total_max_clo_score": sum(r["max_clo_score"] for r in clo_results),
            "total_weighted_clo_score": sum(r["weighted_clo_score"] for r in clo_results),
            "total_normalized_clo_score": sum(r["normalized_clo_score"] for r in clo_results),
            "total_average_bloom_score": sum(r["average_bloom_score"] for r in clo_results),
            "total_weighted_bloom_score": sum(r["weighted_bloom_score"] for r in clo_results)
        }
        
        # Store in session
        session["clo_q_data"] = clo_q_data
        session["clo_results"] = clo_results
        session["total_clo_results"] = total_clo_results
        
        # Debug: Session'a kaydedilen değerleri kontrol et
        print("=== DEBUG: Session'a kaydedilen CLO Results ===")
        for i, result in enumerate(clo_results):
            print(f"CLO {i+1}: normalized_clo_score = {result.get('normalized_clo_score', 'NOT FOUND')}")
        print("=== END DEBUG ===")
        
        # Debug: Session'daki öğrenci verilerini kontrol et
        print("=== DEBUG: Session'daki öğrenci verileri ===")
        if 'students' in session:
            print(f"Öğrenci sayısı: {len(session['students'])}")
            for i, student in enumerate(session['students'][:3]):  # İlk 3 öğrenciyi göster
                print(f"Öğrenci {i+1}: grades = {student.get('grades', [])[:5]}...")  # İlk 5 notu göster
        else:
            print("Session'da öğrenci verisi YOK!")
        print("=== END DEBUG ===")
    
    return render_template(
        "bloom_mapping.html",
        exams=exams,
        clos=list(range(clo_count)),  # 0'dan başlayarak clo_count-1'e kadar
        clo_names=clo_names,
        clo_results=clo_results,
        enumerate=enumerate,
        session=session
    )


# ... (Diğer fonksiyonlar) ...

@app.route("/summary")
def summary():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))

    exams = session.get("exams", [])
    students = session.get("students", [])
    question_points = session.get("question_points")
    
    if not exams or not students or not question_points:
        return redirect(url_for("main"))

    # Sınav ağırlıklarını topla
    total_weight = sum(exam['weight'] for exam in exams)

    # Öğrenci genel puanlarını ve sınav toplamlarını hesapla
    for student in students:
        student['exam_totals'] = []
        student['overall_total'] = 0.0
        
        q_idx_counter = 0
        for exam_idx, exam in enumerate(exams):
            exam_score = 0
            for q_idx in range(int(exam['question_count'])):
                grade_val = 0
                if q_idx_counter < len(student.get('grades', [])):
                    grade_val = student['grades'][q_idx_counter]
                if grade_val is None:
                    grade_val = 0
                exam_score += grade_val
                q_idx_counter += 1
            student['exam_totals'].append(round(exam_score, 2))
            
            if total_weight > 0:
                student['overall_total'] += (exam_score * exam['weight']) / total_weight
    
    # Tüm sorular için istatistikleri (ortalama, medyan, vb.) hesapla
    all_questions_flat = []
    stats = []
    exam_total_stats = []

    global_q_idx_counter = 0
    question_performance_medians = []  # Yeni: her soru için ortalamayı burada topla
    for exam_idx, exam in enumerate(exams):
        exam_grades = []
        total_possible_points_for_exam = 0
        for q_idx_in_exam in range(int(exam['question_count'])):
            # question_points nested yapısından max_points'i al
            max_points = 0
            if (exam_idx < len(question_points) and 
                len(question_points[exam_idx]) > 0):
                # Bu soru için ilk kaydın points'ini al (birden fazla CLO olabilir)
                q_records = [rec for rec in question_points[exam_idx] if rec.get('question_idx', q_idx_in_exam) == q_idx_in_exam]
                if q_records:
                    max_points = q_records[0]['points']
            
            total_possible_points_for_exam += max_points

            all_questions_flat.append({
                'exam_idx': exam_idx,
                'question_idx_in_exam': q_idx_in_exam,
                'global_question_idx': global_q_idx_counter,
                'max_points': max_points
            })

            grades_for_question = [s['grades'][global_q_idx_counter] for s in students]
            grades_for_question = [g for g in grades_for_question if g is not None]

            if grades_for_question:
                avg_val = np.mean(grades_for_question)
                median_val = np.median(grades_for_question)
                perf_avg = round((avg_val / max_points) * 100, 2) if max_points > 0 else 0
                stats.append({
                    'avg': round(avg_val, 2),
                    'median': round(median_val, 2),
                    'max': round(np.max(grades_for_question), 2),
                    'min': round(np.min(grades_for_question), 2),
                    'performance_median': perf_avg
                })
                question_performance_medians.append(perf_avg)
            else:
                stats.append({'avg': 0, 'median': 0, 'max': 0, 'min': 0, 'performance_median': 0})
                question_performance_medians.append(0)

            global_q_idx_counter += 1
            exam_grades.extend(grades_for_question)
        
        # Her sınav için sınav toplamı istatistiklerini hesapla
        exam_totals_list = [s['exam_totals'][exam_idx] for s in students]
        exam_totals_list = [t for t in exam_totals_list if t is not None]

        if exam_totals_list:
            avg_exam_total = np.mean(exam_totals_list)
            median_exam_total = np.median(exam_totals_list)
            exam_total_stats.append({
                'avg': round(avg_exam_total, 2),
                'median': round(median_exam_total, 2),
                'max': round(np.max(exam_totals_list), 2),
                'min': round(np.min(exam_totals_list), 2),
                'performance_median': round((avg_exam_total / total_possible_points_for_exam) * 100, 2) if total_possible_points_for_exam > 0 else 0
            })
        else:
            exam_total_stats.append({'avg': 0, 'median': 0, 'max': 0, 'min': 0, 'performance_median': 0})

    session["question_performance_medians"] = question_performance_medians
    
    # CLO hesaplamalarını her zaman yeniden yap (öğrenci notları güncellendiğinde)
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    
    # Create all_questions_flat_map for bloom mapping
    all_questions_flat_map = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        exam_map = []
        for q_idx_in_exam in range(int(exam['question_count'])):
            exam_map.append(global_q_idx_counter)
            global_q_idx_counter += 1
        all_questions_flat_map.append(exam_map)
    
    # CLO hesaplamalarını yap
    clo_results = []
    for clo_idx in range(1, clo_count+1):
        qct_list, w_list, spm_list, bl_list, ep_list = [], [], [], [], []
        
        # Scan all questions for this CLO
        for exam_idx, exam in enumerate(exams):
            for q in range(exam["question_count"]):
                global_q_idx = all_questions_flat_map[exam_idx][q]
                
                # Bu CLO için bu sorunun verilerini question_points'den al
                q_clo_records = [
                    rec for rec in question_points[exam_idx]
                    if rec['clo'] == clo_idx and rec.get('question_idx', q) == q
                ]
                
                if q_clo_records:
                    rec = q_clo_records[0]
                    qct = rec.get('qct', 0.0)
                    w = rec.get('w', 0.0)
                    bl = rec.get('bl', 0.0)
                    
                    # Calculate SPM value - from student grades (her zaman güncel öğrenci notlarından)
                    spm = 0.0
                    if students:
                        grades_for_question = []
                        for student in students:
                            if global_q_idx < len(student['grades']):
                                try:
                                    grade_val = float(student['grades'][global_q_idx])
                                    grades_for_question.append(grade_val)
                                except (ValueError, TypeError):
                                    continue
                        
                        if grades_for_question:
                            max_points = rec.get('points', 0)
                            if max_points > 0:
                                avg_val = np.mean(grades_for_question)
                                spm = round((avg_val / max_points) * 100, 2)
                    
                    # Sadece bu CLO'ya ait olan soruları ekle
                    if qct > 0 and w > 0:
                        qct_list.append(qct)
                        w_list.append(w)
                        spm_list.append(spm)
                        bl_list.append(bl)
                        ep_list.append(rec.get('points', 0))
        
        # CLO Score hesaplamaları
        max_clo = max_possible_clo_score(qct_list, w_list)
        weighted_clo = weighted_clo_score(qct_list, w_list, spm_list)
        normalized_clo = normalized_clo_score(qct_list, w_list, spm_list, bl_list, ep_list)
        weighted_bloom = weighted_bloom_score(qct_list, w_list, bl_list)
        avg_bloom = average_bloom_score(qct_list, w_list, bl_list)
        
        clo_results.append({
            "max_clo_score": max_clo,
            "weighted_clo_score": weighted_clo,
            "normalized_clo_score": normalized_clo,
            "weighted_bloom_score": weighted_bloom,
            "average_bloom_score": avg_bloom
        })
    
    total_clo_results = {
        "total_max_clo_score": sum(r["max_clo_score"] for r in clo_results),
        "total_weighted_clo_score": sum(r["weighted_clo_score"] for r in clo_results),
        "total_normalized_clo_score": sum(r["normalized_clo_score"] for r in clo_results),
        "total_average_bloom_score": sum(r["average_bloom_score"] for r in clo_results),
        "total_weighted_bloom_score": sum(r["weighted_bloom_score"] for r in clo_results)
    }
    
    # Session'a kaydet (her zaman güncel değerler)
    session["clo_results"] = clo_results
    session["total_clo_results"] = total_clo_results
    
    return render_template(
        "summary.html", 
        exams=exams, 
        students=students, 
        all_questions_flat=all_questions_flat, 
        stats=stats,
        exam_total_stats=exam_total_stats,
        question_points=question_points,
        enumerate=enumerate,
        session=session
    )

@app.route("/download_csv/<int:exam_index>", methods=["POST"])
def download_csv(exam_index):
    course_id = session.get("course_id")
    if not course_id:
        return "Gerekli veriler oturumda bulunamadı.", 400
    
    course = Course.query.get(course_id)
    if not course:
        return "Kurs bulunamadı.", 404

    exams = course.exams
    all_questions_flat = []
    student_count = session.get("student_count")

    if not exams or not all_questions_flat:
        return "Gerekli veriler oturumda bulunamadı.", 400

    exam_name = exams[exam_index].name
    exam_data = []
    current_exam_questions = [q for q in all_questions_flat if q['exam_idx'] == exam_index]
    total_questions_count = len(all_questions_flat)

    for student_idx in range(int(student_count)):
        student_row = {'Öğrenci No': request.form.get(f"student_number_{student_idx}", ''), 
                       'Ad-Soyad': request.form.get(f"student_name_{student_idx}", '')}

        total_grade_for_exam = 0.0
        for q in current_exam_questions:
            global_q_idx = q['global_question_idx']
            grade_key = f"grade_{student_idx}_{global_q_idx}"
            grade_value = float(request.form.get(grade_key, '0.0'))
            student_row[f"Soru_{q['question_idx_in_exam'] + 1} ({q['max_points']})"] = grade_value
            total_grade_for_exam += grade_value

        student_row[f"{exam_name} Toplam"] = total_grade_for_exam
        exam_data.append(student_row)

    # Manual CSV creation instead of pandas
    output = io.StringIO()
    output.write("sep=;\n")
    if exam_data:
        # Header
        headers = list(exam_data[0].keys())
        output.write(';'.join(headers) + '\n')
        
        # Data rows
        for row in exam_data:
            csv_row = []
            for header in headers:
                cell = row.get(header, '')
                csv_row.append(format_csv_cell(cell))
            output.write(';'.join(csv_row) + '\n')
    
    bom = '\ufeff'
    csv_output = bom + output.getvalue()

    response = make_response(csv_output)
    course_code = course.course_code
    response.headers["Content-Disposition"] = f"attachment; filename={course_code}_{exam_name.replace(' ', '_')}_notlari.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

@app.route("/download_clo_csv")
def download_clo_csv():
    course_id = session.get("course_id")
    if not course_id:
        return "CLO verisi bulunamadı.", 404
    
    course = Course.query.get(course_id)
    if not course:
        return "Kurs bulunamadı.", 404

    clo_table = []
    for clo in course.clos:
        clo_table.append({
            'id': clo.id,
            'name': clo.name,
            'order': clo.order
        })
        
    if not clo_table:
        return "CLO verisi bulunamadı.", 404
        
    # Manual CSV creation instead of pandas
    output = io.StringIO()
    output.write("sep=;\n")
    if clo_table:
        # Header (without 'id')
        headers = ['name', 'order']
        output.write(';'.join(headers) + '\n')
        
        # Data rows
        for row in clo_table:
            csv_row = []
            for header in headers:
                cell = row.get(header, '')
                csv_row.append(format_csv_cell(cell))
            output.write(';'.join(csv_row) + '\n')
    
    bom = '\ufeff'
    csv_output = bom + output.getvalue()

    response = make_response(csv_output)
    course_code = course.course_code
    response.headers["Content-Disposition"] = f"attachment; filename={course_code}_clo_details.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

@app.route("/download_clo_analysis_csv")
def download_clo_analysis_csv():
    course_id = session.get("course_id")
    if not course_id:
        return "CLO Analysis verisi bulunamadı.", 404
    
    course = Course.query.get(course_id)
    if not course:
        return "Kurs bulunamadı.", 404

    clo_results = session.get('clo_results', [])
    clo_names = session.get('clo_names', [])
    
    if not clo_results:
        return "CLO Analysis verisi bulunamadı.", 404
    
    # CLO Analysis Results tablosu için veri hazırla
    analysis_data = []
    for clo_idx in range(len(clo_results)):
        # Normalized CLO değerini doğrudan clo_results'dan al
        normalized_clo = clo_results[clo_idx].get('normalized_clo_score', 0)
        # Average Bloom Level-CLO hesaplaması düzeltildi
        avg_bloom_level = clo_results[clo_idx].get('average_bloom_score', 0)
        
        # Performance ve recommendation belirleme
        if normalized_clo >= 85 and avg_bloom_level > 3.0:
            performance_text = "Very high achievement supported by sustained higher-order cognitive engagement"
            recommendation_text = "Maintain current instructional and assessment design; disseminate as internal benchmark practice"
        elif normalized_clo >= 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "High achievement primarily driven by mid-level cognitive processes"
            recommendation_text = "Increase assessment cognitive depth while preserving effective instructional structure"
        elif normalized_clo >= 85 and avg_bloom_level < 2:
            performance_text = "High scores driven by low-cognitive-demand tasks rather than deep understanding"
            recommendation_text = "Redesign assessments to emphasize application, analysis, and reasoning over recall"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level > 3.0:
            performance_text = "Good achievement under cognitively demanding assessment conditions"
            recommendation_text = "Sustain cognitive rigor while strengthening instructional support mechanisms"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Adequate to good achievement with appropriately balanced cognitive demand"
            recommendation_text = "Incrementally introduce higher-order tasks to extend learning beyond procedural competence"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level < 2:
            performance_text = "Acceptable scores achieved through low-depth cognitive activities"
            recommendation_text = "Replace recall-focused questions with application- and analysis-oriented tasks"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level > 3.0:
            performance_text = "Limited achievement despite exposure to high-level cognitive demands"
            recommendation_text = "Enhance scaffolding, feedback, and conceptual clarity to support student success"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Partial achievement based on routine or procedural learning"
            recommendation_text = "Realign instructional delivery and assessment difficulty to improve outcome attainment"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level < 2:
            performance_text = "Minimal learning evidenced, restricted to recall or basic comprehension"
            recommendation_text = "Comprehensively revise teaching strategies and assessment design to promote deeper learning"
        elif normalized_clo < 50 and avg_bloom_level > 3.0:
            performance_text = "Failure to meet outcomes under cognitively demanding assessments"
            recommendation_text = "Rebuild foundational understanding and introduce progressive cognitive scaffolding"
        elif normalized_clo < 50 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Low achievement even with moderate cognitive challenge"
            recommendation_text = "Intensify student support, adjust topic sequencing, and expand guided practice"
        elif normalized_clo < 50 and avg_bloom_level < 2:
            performance_text = "Severe learning deficiency with weak performance and low cognitive demand"
            recommendation_text = "Implement full instructional and assessment redesign as an immediate improvement priority"
        else:
            performance_text = "No data available for assessment"
            recommendation_text = "Please ensure all data is properly entered"
        
        analysis_data.append({
            'CLO': clo_names[clo_idx] if clo_idx < len(clo_names) else f'CLO {clo_idx + 1}',
            'Normalized CLO %': f'="{normalized_clo:.2f}"'.replace('.', ','),
            'Average Bloom Level-CLO': round(avg_bloom_level, 2),
            'Student Performance Assessment': performance_text,
            'Recommended Instructor Action': recommendation_text
        })
    
    # Manual CSV creation instead of pandas
    output = io.StringIO()
    output.write("sep=;\n")
    if analysis_data:
        # Header
        headers = list(analysis_data[0].keys())
        output.write(';'.join(headers) + '\n')
        
        # Data rows
        for row in analysis_data:
            csv_row = []
            for header in headers:
                cell = row.get(header, '')
                csv_row.append(format_csv_cell(cell))
            output.write(';'.join(csv_row) + '\n')
    
    bom = '\ufeff'
    csv_output = bom + output.getvalue()

    response = make_response(csv_output)
    course_code = course.course_code
    response.headers["Content-Disposition"] = f"attachment; filename={course_code}_clo_analysis_results.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

@app.route("/download_all_tables")
def download_all_tables():
    """Tüm tabloları tek bir CSV dosyasında birleştirip indir"""
    course_id = session.get("course_id")
    if not course_id:
        return "Gerekli veriler bulunamadı.", 404
    
    course = Course.query.get(course_id)
    if not course:
        return "Kurs bulunamadı.", 404

    exams = course.exams
    students = session.get('students', [])
    clo_results = session.get('clo_results', [])
    clo_names = session.get('clo_names', [])
    all_questions_flat = session.get('all_questions_flat', [])
    stats = session.get('stats', [])
    exam_total_stats = session.get('exam_total_stats', [])
    
    if not exams or not students:
        return "Gerekli veriler bulunamadı.", 404
    
    # Tüm tabloları alt alta birleştirmek için liste oluştur
    all_rows = []
    
    # 1. Student Grades Table
    all_rows.append([])  # Boş satır
    all_rows.append(['STUDENT GRADES TABLE'])
    all_rows.append([])  # Boş satır
    
    # Öğrenci notları başlıkları
    student_headers = ['Student No', 'Name']
    for exam_idx, exam in enumerate(exams):
        for question in all_questions_flat:
            if question['exam_idx'] == exam_idx:
                question_name = f"{exam.name}_Q{question['question_idx_in_exam'] + 1}"
                student_headers.append(question_name)
        student_headers.append(f"{exam.name}_Total")
    student_headers.append('Overall Total')
    all_rows.append(student_headers)
    
    # Öğrenci notları verileri
    for student in students:
        row = [
            student.get('number', ''),
            student.get('name', ''),
        ]
        
        # Her sınav için soru notları
        for exam_idx, exam in enumerate(exams):
            for question in all_questions_flat:
                if question['exam_idx'] == exam_idx:
                    grade = student['grades'][question['global_question_idx']] if question['global_question_idx'] < len(student['grades']) else 0
                    row.append(grade)
            
            # Sınav toplamı
            exam_total = student.get('exam_totals', [])[exam_idx] if exam_idx < len(student.get('exam_totals', [])) else 0
            row.append(exam_total)
        
        # Genel toplam
        row.append(student.get('overall_total', 0))
        all_rows.append(row)
    
    # 2. CLO Performance Values Table
    all_rows.append([])  # Boş satır
    all_rows.append(['CLO PERFORMANCE VALUES TABLE'])
    all_rows.append([])  # Boş satır
    
    # CLO Performance Values başlıkları
    clo_performance_headers = ['CLO', 'Max CLO Score', 'CLO Score', 'MW-BL', 'Weighted BL Sum']
    all_rows.append(clo_performance_headers)
    
    # CLO Performance Values verileri
    for clo_idx in range(len(clo_results)):
        clo_result = clo_results[clo_idx]
        row = [
            clo_names[clo_idx] if clo_idx < len(clo_names) else f'CLO {clo_idx + 1}',
            clo_result.get('max_clo_score', 0),
            clo_result.get('weighted_clo_score', 0),
            clo_result.get('average_bloom_score', 0),
            clo_result.get('weighted_bloom_score', 0),
        ]
        all_rows.append(row)
    
    # 3. CLO Analysis Results
    all_rows.append([])  # Boş satır
    all_rows.append(['CLO ANALYSIS RESULTS TABLE'])
    all_rows.append([])  # Boş satır
    
    # CLO Analiz başlıkları
    clo_headers = ['CLO', 'Normalized CLO %', 'Average Bloom Level-CLO', 'Student Performance Assessment', 'Recommended Instructor Action']
    all_rows.append(clo_headers)
    
    # CLO Analiz verileri
    for clo_idx in range(len(clo_results)):
        # Normalized CLO değerini doğrudan clo_results'dan al
        normalized_clo = clo_results[clo_idx].get('normalized_clo_score', 0)
        avg_bloom_level = clo_results[clo_idx].get('average_bloom_score', 0)
        
        # Performance ve recommendation belirleme
        if normalized_clo >= 85 and avg_bloom_level > 3.0:
            performance_text = "Very high achievement supported by sustained higher-order cognitive engagement"
            recommendation_text = "Maintain current instructional and assessment design; disseminate as internal benchmark practice"
        elif normalized_clo >= 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "High achievement primarily driven by mid-level cognitive processes"
            recommendation_text = "Increase assessment cognitive depth while preserving effective instructional structure"
        elif normalized_clo >= 85 and avg_bloom_level < 2:
            performance_text = "High scores driven by low-cognitive-demand tasks rather than deep understanding"
            recommendation_text = "Redesign assessments to emphasize application, analysis, and reasoning over recall"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level > 3.0:
            performance_text = "Good achievement under cognitively demanding assessment conditions"
            recommendation_text = "Sustain cognitive rigor while strengthening instructional support mechanisms"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Adequate to good achievement with appropriately balanced cognitive demand"
            recommendation_text = "Incrementally introduce higher-order tasks to extend learning beyond procedural competence"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level < 2:
            performance_text = "Acceptable scores achieved through low-depth cognitive activities"
            recommendation_text = "Replace recall-focused questions with application- and analysis-oriented tasks"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level > 3.0:
            performance_text = "Limited achievement despite exposure to high-level cognitive demands"
            recommendation_text = "Enhance scaffolding, feedback, and conceptual clarity to support student success"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Partial achievement based on routine or procedural learning"
            recommendation_text = "Realign instructional delivery and assessment difficulty to improve outcome attainment"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level < 2:
            performance_text = "Minimal learning evidenced, restricted to recall or basic comprehension"
            recommendation_text = "Comprehensively revise teaching strategies and assessment design to promote deeper learning"
        elif normalized_clo < 50 and avg_bloom_level > 3.0:
            performance_text = "Failure to meet outcomes under cognitively demanding assessments"
            recommendation_text = "Rebuild foundational understanding and introduce progressive cognitive scaffolding"
        elif normalized_clo < 50 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Low achievement even with moderate cognitive challenge"
            recommendation_text = "Intensify student support, adjust topic sequencing, and expand guided practice"
        elif normalized_clo < 50 and avg_bloom_level < 2:
            performance_text = "Severe learning deficiency with weak performance and low cognitive demand"
            recommendation_text = "Implement full instructional and assessment redesign as an immediate improvement priority"
        else:
            performance_text = "No data available for assessment"
            recommendation_text = "Please ensure all data is properly entered"
        
        row = [
            clo_names[clo_idx] if clo_idx < len(clo_names) else f'CLO {clo_idx + 1}',
            f"{normalized_clo:.2f}".replace('.', ',') + '%',
            avg_bloom_level,
            performance_text,
            recommendation_text,
        ]
        all_rows.append(row)
    
    # CSV dosyası oluştur
    output = io.StringIO()
    output.write("sep=;\n")
    for row in all_rows:
        # Her satırı CSV formatında yaz
        csv_row = []
        for cell in row:
            csv_row.append(format_csv_cell(cell))
        output.write(';'.join(csv_row) + '\n')
    
    # BOM ekle (Türkçe karakterler için)
    bom = '\ufeff'
    csv_output = bom + output.getvalue()
    
    # Response oluştur
    response = make_response(csv_output)
    course_code = course.course_code
    response.headers["Content-Disposition"] = f"attachment; filename={course_code}_all_tables.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    
    return response


@app.route("/download_summary_csv")
def download_summary_csv():
    """Summary sayfasındaki tablolar + CLO Performance Values CSV"""
    course_id = session.get("course_id")
    if not course_id:
        return "Gerekli veriler bulunamadı.", 404

    course = Course.query.get(course_id)
    if not course:
        return "Kurs bulunamadı.", 404

    exams = session.get("exams", []) or course.exams
    students = session.get('students', [])
    clo_results = session.get('clo_results', [])
    clo_names = session.get('clo_names', [])
    all_questions_flat = session.get('all_questions_flat', [])
    stats = session.get('stats', [])
    exam_total_stats = session.get('exam_total_stats', [])

    if not exams or not students:
        return "Gerekli veriler bulunamadı.", 404

    all_rows = []

    # 1. Summary tables (per exam)
    all_rows.append([])
    all_rows.append(['SUMMARY TABLES'])
    all_rows.append([])

    for exam_idx, exam in enumerate(exams):
        exam_name = exam['name'] if isinstance(exam, dict) else exam.name
        all_rows.append([f"{exam_name} Exam"])

        headers = ['Student No', 'Name']
        for question in all_questions_flat:
            if question['exam_idx'] == exam_idx:
                headers.append(f"Question {question['question_idx_in_exam'] + 1}")
        headers.append('Exam Total')
        all_rows.append(headers)

        for student in students:
            row = [student.get('number', ''), student.get('name', '')]
            for question in all_questions_flat:
                if question['exam_idx'] == exam_idx:
                    grade = student['grades'][question['global_question_idx']] if question['global_question_idx'] < len(student['grades']) else 0
                    row.append(grade)
            exam_total = student.get('exam_totals', [])[exam_idx] if exam_idx < len(student.get('exam_totals', [])) else 0
            row.append(exam_total)
            all_rows.append(row)

        # Stats rows
        if stats and exam_total_stats and exam_idx < len(exam_total_stats):
            avg_row = ['Average', '']
            median_row = ['Median', '']
            max_row = ['Max', '']
            min_row = ['Min', '']
            perf_row = ['Student Performance Average (%)', '']
            for question in all_questions_flat:
                if question['exam_idx'] == exam_idx:
                    q_stats = stats[question['global_question_idx']]
                    avg_row.append(q_stats.get('avg', 0))
                    median_row.append(q_stats.get('median', 0))
                    max_row.append(q_stats.get('max', 0))
                    min_row.append(q_stats.get('min', 0))
                    perf_row.append(q_stats.get('performance_median', 0))
            avg_row.append(exam_total_stats[exam_idx].get('avg', 0))
            median_row.append(exam_total_stats[exam_idx].get('median', 0))
            max_row.append(exam_total_stats[exam_idx].get('max', 0))
            min_row.append(exam_total_stats[exam_idx].get('min', 0))
            perf_row.append(exam_total_stats[exam_idx].get('performance_median', 0))

            all_rows.append(avg_row)
            all_rows.append(median_row)
            all_rows.append(max_row)
            all_rows.append(min_row)
            all_rows.append(perf_row)

        all_rows.append([])

    # 2. Overall Results table
    all_rows.append(['OVERALL RESULTS'])
    overall_headers = ['Student No', 'Name']
    for exam in exams:
        exam_name = exam['name'] if isinstance(exam, dict) else exam.name
        exam_weight = exam['weight'] if isinstance(exam, dict) else exam.weight
        overall_headers.append(f"{exam_name} Notu ({exam_weight}%)")
    overall_headers.append('Overall Total (100)')
    all_rows.append(overall_headers)

    for student in students:
        row = [student.get('number', ''), student.get('name', '')]
        for exam_total in student.get('exam_totals', []):
            row.append(exam_total)
        row.append(student.get('overall_total', 0))
        all_rows.append(row)

    # 3. CLO Performance Values Table
    all_rows.append([])
    all_rows.append(['CLO PERFORMANCE VALUES TABLE'])
    all_rows.append([])

    clo_performance_headers = ['CLO', 'Max CLO Score', 'CLO Score', 'MW-BL', 'Weighted BL Sum']
    all_rows.append(clo_performance_headers)

    for clo_idx in range(len(clo_results)):
        clo_result = clo_results[clo_idx]
        row = [
            clo_names[clo_idx] if clo_idx < len(clo_names) else f'CLO {clo_idx + 1}',
            clo_result.get('max_clo_score', 0),
            clo_result.get('weighted_clo_score', 0),
            clo_result.get('average_bloom_score', 0),
            clo_result.get('weighted_bloom_score', 0),
        ]
        all_rows.append(row)

    output = io.StringIO()
    output.write("sep=;\n")
    for row in all_rows:
        csv_row = []
        for cell in row:
            csv_row.append(format_csv_cell(cell))
        output.write(';'.join(csv_row) + '\n')

    bom = '\ufeff'
    csv_output = bom + output.getvalue()

    response = make_response(csv_output)
    course_code = course.course_code
    response.headers["Content-Disposition"] = f"attachment; filename={course_code}_summary_tables.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

# MANUAL CALCULATION FUNCTIONS (numpy replacement)
def manual_mean(values):
    """Manuel ortalama hesaplama"""
    if not values:
        return 0
    return sum(values) / len(values)

def manual_median(values):
    """Manuel medyan hesaplama"""
    if not values:
        return 0
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        return sorted_values[n//2]

def manual_max(values):
    """Manuel maksimum hesaplama"""
    if not values:
        return 0
    return max(values)

def manual_min(values):
    """Manuel minimum hesaplama"""
    if not values:
        return 0
    return min(values)

# CALCULATION FUNCTIONS
def max_possible_clo_score(qct_list, w_list):
    """Maksimum mümkün CLO skoru hesapla"""
    if not qct_list or not w_list or len(qct_list) != len(w_list):
        return 0
    return sum((qct / 100) * w for qct, w in zip(qct_list, w_list))

def weighted_clo_score(qct_list, w_list, spm_list):
    """Ağırlıklı CLO skoru hesapla"""
    if not qct_list or not w_list or not spm_list or len(qct_list) != len(w_list) or len(w_list) != len(spm_list):
        return 0
    return sum((qct / 100) * w * (spm / 100) for qct, w, spm in zip(qct_list, w_list, spm_list))

def normalized_clo_score(qct_list, w_list, spm_list, bl_list=None, ep_list=None):
    """Normalize edilmiş CLO skoru hesapla - yüzde olarak (BL ağırlıklı)"""
    if (not w_list or not spm_list or not qct_list or not bl_list or
        len(qct_list) != len(w_list) or len(w_list) != len(spm_list) or len(spm_list) != len(bl_list)):
        print(
            "normalized_clo_score: Invalid input lengths - "
            f"qct:{len(qct_list)}, w:{len(w_list)}, spm:{len(spm_list)}, bl:{len(bl_list)}"
        )
        return 0

    # Normalized CLO % = SUMPRODUCT(CLO Score, Bloom Weight) / SUMPRODUCT(Max CLO Score, Bloom Weight) * 100
    # CLO Score per question = (QCT/100) * W * (SPM/100)
    # Max CLO Score per question = (QCT/100) * W
    # Bloom Weight is a percentage; convert to coefficient by dividing by 100
    numerator = sum((qct / 100) * w * (spm / 100) * (bl / 100) for qct, w, spm, bl in zip(qct_list, w_list, spm_list, bl_list))
    denominator = sum((qct / 100) * w * (bl / 100) for qct, w, bl in zip(qct_list, w_list, bl_list))

    print(f"normalized_clo_score: numerator = {numerator}, denominator = {denominator}")

    if denominator > 0:
        result = (numerator / denominator) * 100
        print(f"normalized_clo_score: Final calculation: ({numerator} / {denominator}) * 100 = {result}")
        return result

    print("normalized_clo_score: denominator is 0 - this should not happen with valid data")
    return 0

def weighted_bloom_score(qct_list, w_list, bl_list):
    """Ağırlıklı Bloom skoru hesapla"""
    if not qct_list or not w_list or not bl_list or len(qct_list) != len(w_list) or len(w_list) != len(bl_list):
        return 0
    return sum((qct / 100) * w * bl for qct, w, bl in zip(qct_list, w_list, bl_list))

def average_bloom_score(qct_list, w_list, bl_list):
    """Ortalama Bloom seviyesi hesapla - Weighted BL Sum / MW-BL"""
    if not qct_list or not w_list or not bl_list or len(qct_list) != len(w_list) or len(w_list) != len(bl_list):
        return 0
    
    # Sadece pozitif değerleri olan soruları al
    valid_data = [(qct, w, bl) for qct, w, bl in zip(qct_list, w_list, bl_list) if qct > 0 and w > 0]
    
    if not valid_data:
        return 0
    
    # Average Bloom Score = Weighted BL Sum / MW-BL
    # Weighted BL Sum = Σ(QCTᵢ/100 × Wᵢ × BLᵢ)
    # MW-BL = Σ(QCTᵢ/100 × Wᵢ)
    weighted_bloom_sum = sum((qct / 100) * w * bl for qct, w, bl in valid_data)
    mw_bl = sum((qct / 100) * w for qct, w, _ in valid_data)
    
    return weighted_bloom_sum / mw_bl if mw_bl > 0 else 0

# AJAX Save Routes
@app.route("/save_exam_data", methods=["POST"])
def save_exam_data():
    """AJAX ile sınav verilerini kaydet"""
    try:
        course_id = session.get("course_id")
        if not course_id:
            return jsonify({"success": False, "error": "Kurs bulunamadı"})
        
        data = request.get_json()
        exam_idx = data.get("exam_idx")
        students_data = data.get("students", [])
        
        # Veritabanından mevcut sınavı al
        exam_db = Exam.query.filter_by(course_id=course_id).all()
        if exam_idx >= len(exam_db):
            return jsonify({"success": False, "error": "Sınav bulunamadı"})
        
        exam = exam_db[exam_idx]
        
        # Session'dan exams verilerini al
        exams = session.get("exams", [])
        if not exams:
            return jsonify({"success": False, "error": "Sınav verileri bulunamadı"})
        
        # Session'daki mevcut öğrenci verilerini al
        current_session_students = session.get("students", [])
        
        # Her öğrenci için verileri kaydet/güncelle
        for student_data in students_data:
            student_number = student_data.get("number", "")
            student_name = student_data.get("name", "")
            grades = student_data.get("grades", [])
            
            if student_number and student_name:
                # Öğrenciyi bul veya oluştur
                student = Student.query.filter_by(course_id=course_id, number=student_number).first()
                if not student:
                    student = Student(course_id=course_id, number=student_number, name=student_name)
                    db.session.add(student)
                    db.session.flush()
                else:
                    student.name = student_name
                
                # Notları kaydet/güncelle
                for grade_idx, grade_value in enumerate(grades):
                    # Bu grade_idx'e karşılık gelen question'ı bul
                    question = Question.query.filter_by(exam_id=exam.id, question_idx=grade_idx).first()
                    if question:
                        # Not validasyonu - maksimum puanı aşmayı engelle
                        if grade_value > question.max_points:
                            grade_value = question.max_points
                        elif grade_value < 0:
                            grade_value = 0
                        
                        # Mevcut notu bul veya yeni oluştur
                        existing_grade = Grade.query.filter_by(student_id=student.id, question_id=question.id).first()
                        if existing_grade:
                            existing_grade.grade = grade_value
                        else:
                            new_grade = Grade(student_id=student.id, question_id=question.id, grade=grade_value)
                            db.session.add(new_grade)
                
                # Session'daki öğrenci verilerini güncelle - sadece bu sınavın notlarını güncelle
                session_student_found = False
                for session_student in current_session_students:
                    if session_student.get("number") == student_number:
                        session_student["name"] = student_name
                        
                        # Bu sınavın başlangıç indeksini bul
                        start_idx = 0
                        for i in range(exam_idx):
                            start_idx += int(exams[i]['question_count'])
                        
                        # Sadece bu sınavın notlarını güncelle
                        for i, grade in enumerate(grades):
                            if start_idx + i < len(session_student["grades"]):
                                session_student["grades"][start_idx + i] = grade
                        
                        # Toplamı yeniden hesapla
                        session_student["total"] = sum(g for g in session_student["grades"] if g not in [None])
                        session_student_found = True
                        break
                
                # Eğer session'da yoksa ekle
                if not session_student_found:
                    # Tüm sınavlar için boş notlar oluştur
                    all_grades = [0.0] * sum(int(exam['question_count']) for exam in exams)
                    
                    # Bu sınavın notlarını yerleştir
                    start_idx = 0
                    for i in range(exam_idx):
                        start_idx += int(exams[i]['question_count'])
                    
                    for i, grade in enumerate(grades):
                        if start_idx + i < len(all_grades):
                            all_grades[start_idx + i] = grade
                    
                    current_session_students.append({
                        "number": student_number,
                        "name": student_name,
                        "grades": all_grades,
                        "total": sum(g for g in all_grades if g not in [None])
                    })
        
        # Session'ı güncelle
        session["students"] = current_session_students
        
        # Debug: Session'a kaydedilen verileri kontrol et
        print(f"=== DEBUG: save_exam_data - Session'a kaydedilen öğrenci sayısı: {len(current_session_students)} ===")
        for i, student in enumerate(current_session_students[:3]):  # İlk 3 öğrenciyi göster
            print(f"Öğrenci {i+1}: {student.get('name', 'N/A')} - grades = {student.get('grades', [])[:5]}...")
        
        db.session.commit()
        return jsonify({"success": True, "message": "Veriler başarıyla kaydedildi"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

@app.route("/save_bloom_mapping", methods=["POST"])
def save_bloom_mapping():
    """AJAX ile Bloom Mapping verilerini kaydet"""
    try:
        course_id = session.get("course_id")
        if not course_id:
            return jsonify({"success": False, "error": "Kurs bulunamadı"})
        
        data = request.get_json()
        
        # Bloom mapping verilerini session'a kaydet
        session["bloom_mapping_data"] = data
        
        # Veritabanına da kaydet (gerekirse)
        # Bu kısım bloom mapping verilerini veritabanında saklamak için genişletilebilir
        
        return jsonify({"success": True, "message": "Bloom Mapping verileri başarıyla kaydedildi"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Veritabanı yedekleme ve geri yükleme fonksiyonları
@app.route("/backup_database")
def backup_database():
    """Veritabanını yedekle"""
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"evaluation_system_backup_{timestamp}.db"
        
        # Veritabanı dosyasını kopyala
        shutil.copy2("evaluation_system.db", backup_name)
        
        return f"✅ Veritabanı başarıyla yedeklendi: {backup_name}"
    except Exception as e:
        return f"❌ Yedekleme hatası: {str(e)}"

@app.route("/restore_database/<filename>")
def restore_database(filename):
    """Veritabanını geri yükle"""
    try:
        import shutil
        
        backup_file = f"evaluation_system_backup_{filename}.db"
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, "evaluation_system.db")
            return f"✅ Veritabanı başarıyla geri yüklendi: {backup_file}"
        else:
            return f"❌ Yedek dosya bulunamadı: {backup_file}"
    except Exception as e:
        return f"❌ Geri yükleme hatası: {str(e)}"

if __name__ == "__main__":
    with app.app_context():
        if RESET_DB_ON_START:
            db_paths = {
                DB_FILEPATH,
                os.path.join(app.root_path, DB_FILENAME),
                os.path.join(os.getcwd(), DB_FILENAME),
            }
            for path in db_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass
        db.create_all()

    app.run(host='0.0.0.0', port=8080, debug=True)
    
    
    
    
    
