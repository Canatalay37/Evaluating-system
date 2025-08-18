import os
from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import numpy as np
import io
import openpyxl 
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Veritabanı yapılandırması
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///evaluation_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Veritabanı Modelleri
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(50), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
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
    
    # İlişkiler
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')

class CLO(db.Model):
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
    
    # İlişkiler
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
    
    # İlişkiler
    grades = db.relationship('Grade', backref='student', lazy=True, cascade='all, delete-orphan')

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    grade = db.Column(db.Float, nullable=False)

# Veritabanını oluştur
with app.app_context():
    db.create_all()

# ROUTES
@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        # Get course information
        course_code = request.form["course_code"]
        teacher_name = request.form["teacher_name"]
        semester = request.form["semester"]
        
        exam_count = int(request.form["exam_count"])
        # Her sınav için ayrı öğrenci sayısı (liste)
        students_per_exam = []
        for i in range(exam_count):
            val = request.form.get(f"students_per_exam_{i}", "0")
            try:
                students_per_exam.append(int(val))
            except ValueError:
                students_per_exam.append(0)
        # Toplam öğrenci sayısı (özellikle student_grades için var olan mantığı korumak üzere maksimumu al)
        student_count = max(students_per_exam) if students_per_exam else 0
        
        # Veritabanına kaydet
        course = Course(
            course_code=course_code,
            teacher_name=teacher_name,
            semester=semester
        )
        db.session.add(course)
        db.session.commit()
        
        # Session'a course_id'yi kaydet
        session["course_id"] = course.id
        session["course_code"] = course_code
        session["teacher_name"] = teacher_name
        session["semester"] = semester
        session["exam_count"] = exam_count
        session["student_count"] = student_count
        session["students_per_exam"] = students_per_exam
        session.pop("exams", None) 
        session.pop("question_points", None)
        session.pop("clos", None) 
        session.pop("students", None)
        session.pop("clo_q_data", None)
        session.pop("clo_results", None)
        session.pop("total_clo_results", None)
        session.pop("clo_count", None)
        session.pop("clo_names", None)
        return redirect(url_for("exam_details"))
    return render_template("main.html")

@app.route("/exam_details", methods=["GET", "POST"])
def exam_details():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))
    
    if request.method == "POST":
        # Process CLO configuration
        clo_count = int(request.form.get("clo_count", 10))
        clo_names = []
        for i in range(clo_count):
            clo_name = request.form.get(f"clo_name_{i}", f"CLO {i+1}")
            clo_names.append(clo_name)
        
        # CLO'ları veritabanına kaydet
        for i, name in enumerate(clo_names):
            clo = CLO(course_id=course_id, name=name, order=i+1)
            db.session.add(clo)
        
        # Process exam details
        exams = []
        for i in range(session["exam_count"]):
            exam = Exam(
                course_id=course_id,
                name=request.form[f"exam_name_{i}"],
                question_count=int(request.form[f"question_count_{i}"]),
                weight=int(request.form[f"weight_{i}"]),
                students_per_exam=session["students_per_exam"][i]
            )
            db.session.add(exam)
            exams.append(exam)
        
        db.session.commit()
        
        # Session'a güncelle
        session["exams"] = [{"name": e.name, "question_count": e.question_count, "weight": e.weight} for e in exams]
        session["clo_count"] = clo_count
        session["clo_names"] = clo_names
        
        return redirect(url_for("question_points"))

    # Get existing CLO configuration for display
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    
    return render_template("exam_details.html", 
                         exam_count=session.get("exam_count", 0), 
                         clo_count=clo_count,
                         clo_names=clo_names,
                         enumerate=enumerate,
                         session=session)

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
    
    if not exams:
        return redirect(url_for("exam_details"))
    
    if request.method == "POST":
        # Sunucu tarafı doğrulama: her sınavın soru puanları toplamı 100 olmalı
        question_points_list = []
        for idx, exam in enumerate(exams):
            running_sum = 0.0
            questions = []
            for q in range(int(exam["question_count"])):
                points = float(request.form.get(f"points_{idx}_{q}", 0))
                running_sum += points
                clo_keys = request.form.getlist(f"clo_{idx}_{q}")
                selected_clos = [int(c) for c in clo_keys]
                # QCT değerini otomatik hesapla: (Soru puanı × Sınav yüzdesi) ÷ 100
                qct = (points * exam["weight"]) / 100
                bl = float(request.form.get(f"bl_{idx}_{q}", 0))
                n_clo = len(selected_clos)
                w_val = 1.0 / n_clo if n_clo > 0 else 0.0
                
                # Question'ı veritabanına kaydet
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
                    
                    # CLO mapping'leri kaydet
                    for clo_idx in selected_clos:
                        clo = CLO.query.filter_by(course_id=course_id, order=clo_idx).first()
                        if clo:
                            mapping = QuestionCLOMapping(question_id=question.id, clo_id=clo.id)
                            db.session.add(mapping)
                        else:
                            # CLO bulunamadıysa log ekle
                            print(f"CLO with order {clo_idx} not found for course {course_id}")
                            # Hata durumunda kullanıcıya bilgi ver
                            return f"CLO {clo_idx} not found for course. Please check CLO configuration.", 400
                    
                    # En az bir CLO seçilmiş olmalı
                    if not selected_clos:
                        return f"Question {q+1} in {exam['name']} must have at least one CLO selected.", 400
                    
                    # QCT artık otomatik hesaplandığı için validation gerekmez
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
                return f"{exams[idx]['name']} için soru puanları toplamı {running_sum}. Toplam 100 olmalı.", 400
        
        db.session.commit()
        session["question_points"] = question_points_list
        return redirect(url_for("student_grades"))
    
    return render_template(
        "question_points.html",
        exams=exams,
        clo_count=clo_count,
        clo_names=clo_names,
        students_per_exam=students_per_exam,
        enumerate=enumerate,
        session=session,
    )

@app.route("/student_grades", methods=["GET", "POST"])
def student_grades():
    course_id = session.get("course_id")
    if not course_id:
        return redirect(url_for("main"))
    
    course = Course.query.get(course_id)
    if not course:
        return redirect(url_for("main"))
    
    # Veritabanından verileri al
    exams_db = Exam.query.filter_by(course_id=course_id).all()
    students_db = Student.query.filter_by(course_id=course_id).all()
    
    # Session'dan verileri al (geriye uyumluluk için)
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

    # students_data'yı veritabanından al veya boş liste olarak başlat
    students_data = []
    if students_db:
        for student in students_db:
            grades = [''] * len(all_questions_flat_for_jinja)
            # Veritabanından grades'ları al
            for grade in student.grades:
                if grade.question_id < len(grades):
                    grades[grade.question_id] = grade.grade
            
            students_data.append({
                "number": student.number,
                "name": student.name,
                "grades": grades,
                "total": sum(g for g in grades if g not in [0, 0.0, '', None])
            })
    else:
        # Boş öğrenci listesi oluştur
        for i in range(student_count):
            students_data.append({
                "number": "",
                "name": "",
                "grades": [''] * len(all_questions_flat_for_jinja),
                "total": 0.0
            })

    if request.method == "POST":
        # Check if this is a bloom mapping form submission
        if any(key.startswith('qct_') or key.startswith('w_') or key.startswith('spm_') or key.startswith('bl_') for key in request.form.keys()):
            # Handle bloom mapping form submission
            clo_count = session.get("clo_count", 10)
            clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
            
            # Form verilerini işle ve session'a kaydet
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
            
            # Hesaplamaları yap
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
                qct_list, w_list, spm_list, bl_list = [], [], [], []
                for exam_idx, exam in enumerate(exams):
                    for q in range(exam["question_count"]):
                        global_q_idx = all_questions_flat_map[exam_idx][q]
                        qct = clo_q_data[clo_idx-1][global_q_idx]['qct']
                        w = clo_q_data[clo_idx-1][global_q_idx]['w']
                        spm = clo_q_data[clo_idx-1][global_q_idx]['spm']
                        bl = clo_q_data[clo_idx-1][global_q_idx]['bl']
                        qct_list.append(qct)
                        w_list.append(w)
                        spm_list.append(spm)
                        bl_list.append(bl)
                clo_results.append({
                    "max_clo_score": max_possible_clo_score(qct_list, w_list),
                    "weighted_clo_score": weighted_clo_score(qct_list, w_list, spm_list),
                    "normalized_clo_score": normalized_clo_score(qct_list, w_list, spm_list),
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
            
            # SPM değerlerini otomatik olarak güncelle
            if 'students' in session and session['students']:
                students = session['students']
                question_performance_medians = []
                global_q_idx_counter = 0
                
                for exam_idx, exam in enumerate(exams):
                    for q_idx_in_exam in range(int(exam['question_count'])):
                        grades_for_question = []
                        for student in students:
                            if (global_q_idx_counter < len(student['grades']) and 
                                student['grades'][global_q_idx_counter] not in [0, 0.0, '', None]):
                                grades_for_question.append(student['grades'][global_q_idx_counter])
                        
                        spm_val = 0.0
                        if grades_for_question:
                            # Max points'i bul
                            max_points = 0
                            for q_rec in question_points_nested[exam_idx]:
                                if q_rec.get('question_idx') == q_idx_in_exam:
                                    max_points = q_rec.get('points', 0)
                                    break
                            
                            if max_points > 0:
                                median_val = np.median(grades_for_question)
                                spm_val = round((median_val / max_points) * 100, 2)
                        
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
                student_grades_list = [0.0] * total_questions_count 

                for q_flat in all_questions_flat_for_jinja:
                    grade_key = f"grade_{student_idx}_{q_flat['global_question_idx']}"
                    grade = request.form.get(grade_key, "0.0")
                    try:
                        grade_value = float(grade)
                    except ValueError:
                        grade_value = 0.0 
                    
                    student_grades_list[q_flat['global_question_idx']] = grade_value
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
                        
                        # Grade'ı veritabanına kaydet/güncelle
                        existing_grade = Grade.query.filter_by(student_id=student.id, question_id=question_global_idx).first()
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
                            
                            # SPM değerini otomatik hesapla
                            spm_val = 0.0
                            if 'students' in session and session['students']:
                                students = session['students']
                                grades_for_question = []
                                for student in students:
                                    if (global_q_idx_counter < len(student['grades']) and 
                                        student['grades'][global_q_idx_counter] not in [0, 0.0, '', None]):
                                        grades_for_question.append(student['grades'][global_q_idx_counter])
                                
                                if grades_for_question:
                                    # Max points'i bul
                                    max_points = 0
                                    for q_rec in question_points_nested[exam_idx]:
                                        if q_rec.get('question_idx') == q_idx_in_exam:
                                            max_points = q_rec.get('points', 0)
                                            break
                                    
                                    if max_points > 0:
                                        median_val = np.median(grades_for_question)
                                        spm_val = round((median_val / max_points) * 100, 2)
                            else:
                                # Eğer öğrenci verisi yoksa, question_performance_medians'dan al
                                question_performance_medians = session.get("question_performance_medians", [])
                                if global_q_idx_counter < len(question_performance_medians):
                                    spm_val = question_performance_medians[global_q_idx_counter]
                            
                            # QCT ve W değerlerini doğru şekilde al
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
            qct_list, w_list, spm_list, bl_list = [], [], [], []
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
                        
                        # SPM değerini hesapla
                        spm = 0.0
                        if 'students' in session and session['students']:
                            students = session['students']
                            grades_for_question = []
                            for student in students:
                                if (global_q_idx < len(student['grades']) and 
                                    student['grades'][global_q_idx] not in [0, 0.0, '', None]):
                                    grades_for_question.append(student['grades'][global_q_idx])
                            
                            if grades_for_question:
                                max_points = rec.get('points', 0)
                                if max_points > 0:
                                    median_val = np.median(grades_for_question)
                                    spm = round((median_val / max_points) * 100, 2)
                        
                        # Sadece bu CLO'ya ait olan soruları ekle
                        if qct > 0 and w > 0:
                            qct_list.append(qct)
                            w_list.append(w)
                            spm_list.append(spm)
                            bl_list.append(bl)
            
            # CLO Score hesaplamaları
            max_clo = max_possible_clo_score(qct_list, w_list)
            weighted_clo = weighted_clo_score(qct_list, w_list, spm_list)
            normalized_clo = normalized_clo_score(qct_list, w_list, spm_list)
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
    
    # Eğer clo_results yoksa, hesaplamaları yap
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
                    # Bu CLO için bu sorunun verilerini bul
                    q_clo_records = [
                        rec for rec in question_points_nested[exam_idx]
                        if rec['clo'] == clo_idx and rec.get('question_idx', q_idx_in_exam) == q_idx_in_exam
                    ]
                    
                    if q_clo_records:
                        rec = q_clo_records[0]
                        # SPM değerini otomatik hesapla
                        spm_val = 0.0
                        if 'students' in session and session['students']:
                            students = session['students']
                            grades_for_question = []
                            for student in students:
                                if (global_q_idx_counter < len(student['grades']) and 
                                    student['grades'][global_q_idx_counter] not in [0, 0.0, '', None]):
                                    grades_for_question.append(student['grades'][global_q_idx_counter])
                            
                            if grades_for_question:
                                # Max points'i bul
                                max_points = 0
                                for q_rec in question_points_nested[exam_idx]:
                                    if q_rec.get('question_idx') == q_idx_in_exam:
                                        max_points = q_rec.get('points', 0)
                                        break
                                
                                if max_points > 0:
                                    median_val = np.median(grades_for_question)
                                    spm_val = round((median_val / max_points) * 100, 2)
                        else:
                            # Eğer öğrenci verisi yoksa, question_performance_medians'dan al
                            question_performance_medians = session.get("question_performance_medians", [])
                            if global_q_idx_counter < len(question_performance_medians):
                                spm_val = question_performance_medians[global_q_idx_counter]
                        
                        # QCT ve W değerlerini doğru şekilde al
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
                        # Bu CLO için bu soru yok, 0 değerleri ata
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
            qct_list, w_list, spm_list, bl_list = [], [], [], []
            
            # Bu CLO için tüm soruları tara
            for exam_idx, exam in enumerate(exams):
                for q in range(exam["question_count"]):
                    global_q_idx = all_questions_flat_map[exam_idx][q]
                    
                    # Bu CLO için bu sorunun verilerini question_points'den al
                    q_clo_records = [
                        rec for rec in question_points_nested[exam_idx]
                        if rec['clo'] == clo_idx and rec.get('question_idx', q) == q
                    ]
                    
                    # Debug: CLO mapping kontrolü
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
                        
                        # SPM değerini hesapla - öğrenci notlarından
                        spm = 0.0
                        if 'students' in session and session['students']:
                            students = session['students']
                            grades_for_question = []
                            for student in students:
                                if (global_q_idx < len(student['grades']) and 
                                    student['grades'][global_q_idx] not in [0, 0.0, '', None, '']):
                                    try:
                                        grade_val = float(student['grades'][global_q_idx])
                                        if grade_val > 0:
                                            grades_for_question.append(grade_val)
                                    except (ValueError, TypeError):
                                        continue
                            
                            if grades_for_question:
                                max_points = rec.get('points', 0)
                                if max_points > 0:
                                    median_val = np.median(grades_for_question)
                                    spm = round((median_val / max_points) * 100, 2)
                                    print(f"CLO {clo_idx}, Q{q+1}: grades={grades_for_question}, median={median_val}, max_points={max_points}, SPM={spm}")
                                else:
                                    print(f"CLO {clo_idx}, Q{q+1}: max_points is 0")
                            else:
                                print(f"CLO {clo_idx}, Q{q+1}: no valid grades found")
                                # Eğer not bulunamazsa, varsayılan bir SPM değeri kullan
                                spm = 50.0  # Varsayılan %50 performans
                                print(f"CLO {clo_idx}, Q{q+1}: using default SPM = {spm}")
                        else:
                            print(f"CLO {clo_idx}, Q{q+1}: no students data in session")
                            # Öğrenci verisi yoksa, varsayılan bir SPM değeri kullan
                            spm = 50.0  # Varsayılan %50 performans
                            print(f"CLO {clo_idx}, Q{q+1}: using default SPM = {spm}")
                        
                        # Sadece bu CLO'ya ait olan soruları ekle
                        if qct > 0 and w > 0:
                            qct_list.append(qct)
                            w_list.append(w)
                            spm_list.append(spm)
                            bl_list.append(bl)
                            
                            print(f"CLO {clo_idx}, Q{q+1}: QCT={qct}, W={w}, SPM={spm}, BL={bl}")
            
            # CLO Score hesaplamaları
            max_clo = max_possible_clo_score(qct_list, w_list)
            weighted_clo = weighted_clo_score(qct_list, w_list, spm_list)
            normalized_clo = normalized_clo_score(qct_list, w_list, spm_list)
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
                exam_score += student['grades'][q_idx_counter]
                q_idx_counter += 1
            student['exam_totals'].append(round(exam_score, 2))
            
            if total_weight > 0:
                student['overall_total'] += (exam_score * exam['weight']) / total_weight
    
    # Tüm sorular için istatistikleri (ortalama, medyan, vb.) hesapla
    all_questions_flat = []
    stats = []
    exam_total_stats = []

    global_q_idx_counter = 0
    question_performance_medians = []  # Yeni: her soru için medyanı burada topla
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
                median_val = np.median(grades_for_question)
                perf_median = round((median_val / max_points) * 100, 2) if max_points > 0 else 0
                stats.append({
                    'avg': round(np.mean(grades_for_question), 2),
                    'median': round(median_val, 2),
                    'max': round(np.max(grades_for_question), 2),
                    'min': round(np.min(grades_for_question), 2),
                    'performance_median': perf_median
                })
                question_performance_medians.append(perf_median)
            else:
                stats.append({'avg': 0, 'median': 0, 'max': 0, 'min': 0, 'performance_median': 0})
                question_performance_medians.append(0)

            global_q_idx_counter += 1
            exam_grades.extend(grades_for_question)
        
        # Her sınav için sınav toplamı istatistiklerini hesapla
        exam_totals_list = [s['exam_totals'][exam_idx] for s in students]
        exam_totals_list = [t for t in exam_totals_list if t is not None]

        if exam_totals_list:
            median_exam_total = np.median(exam_totals_list)
            exam_total_stats.append({
                'avg': round(np.mean(exam_totals_list), 2),
                'median': round(median_exam_total, 2),
                'max': round(np.max(exam_totals_list), 2),
                'min': round(np.min(exam_totals_list), 2),
                'performance_median': round((median_exam_total / total_possible_points_for_exam) * 100, 2) if total_possible_points_for_exam > 0 else 0
            })
        else:
            exam_total_stats.append({'avg': 0, 'median': 0, 'max': 0, 'min': 0, 'performance_median': 0})

    session["question_performance_medians"] = question_performance_medians
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

    df = pd.DataFrame(exam_data)

    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
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
        
    df = pd.DataFrame(clo_table)
    # 'id' sütununu çıkararak daha temiz bir tablo oluşturun
    if 'id' in df.columns:
        df = df.drop(columns=['id'])

    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8', float_format='%.3f')
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
            performance_text = "Excellent mastery with deep, higher-order thinking"
            recommendation_text = "Maintain teaching and assessment strategy; consider sharing as best practice"
        elif normalized_clo >= 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Excellent mastery, but mostly mid-level cognitive tasks"
            recommendation_text = "Improve assessment depth (add BL 4 questions) while retaining core approach"
        elif normalized_clo >= 85 and avg_bloom_level < 2:
            performance_text = "Superficial mastery — strong scores from low-level tasks"
            recommendation_text = "Replace low-level assessments with tasks that demand higher-order thinking"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level > 3.0:
            performance_text = "Strong achievement with rich cognitive engagement"
            recommendation_text = "Maintain rigor; consider refining support strategies for students"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Strong results with balanced cognitive challenge"
            recommendation_text = "Introduce more Bloom Level 3+ tasks to push students beyond procedural skills"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level < 2:
            performance_text = "Strong scores with limited depth — risk of over-simplification"
            recommendation_text = "Shift from recall-based to application/analysis-type questions"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level > 3.0:
            performance_text = "Moderate learning with challenging conditions"
            recommendation_text = "Offer better scaffolding and conceptual clarity to help students succeed"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Moderate achievement with routine or procedural learning"
            recommendation_text = "Revise both instruction and question difficulty for alignment"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level < 2:
            performance_text = "Basic understanding with very limited thinking depth"
            recommendation_text = "Redesign instruction and assessments to encourage deep learning"
        elif normalized_clo < 50 and avg_bloom_level > 3.0:
            performance_text = "Poor achievement on cognitively rich tasks"
            recommendation_text = "Strengthen foundational teaching and reinforce cognitive scaffolding"
        elif normalized_clo < 50 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Low achievement with moderate-level assessment"
            recommendation_text = "Increase student support; revisit topic sequencing, and practice opportunities"
        elif normalized_clo < 50 and avg_bloom_level < 2:
            performance_text = "Critical learning failure — performance and rigor are both weak"
            recommendation_text = "Full instructional and assessment redesign needed — priority for improvement"
        else:
            performance_text = "No data available for assessment"
            recommendation_text = "Please ensure all data is properly entered"
        
        analysis_data.append({
            'CLO': clo_names[clo_idx] if clo_idx < len(clo_names) else f'CLO {clo_idx + 1}',
            'Normalized CLO %': f"{normalized_clo:.2f}%",
            'Average Bloom Level-CLO': f"{avg_bloom_level:.2f}",
            'Student Performance Assessment': performance_text,
            'Recommended Instructor Action': recommendation_text
        })
    
    df = pd.DataFrame(analysis_data)

    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
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
    
    # 1. Öğrenci Notları Tablosu
    student_grades_data = []
    for student in students:
        row = {
            'Student No': student.get('number', ''),
            'Name': student.get('name', ''),
        }
        
        # Her sınav için soru notları
        for exam_idx, exam in enumerate(exams):
            for question in all_questions_flat:
                if question['exam_idx'] == exam_idx:
                    question_name = f"{exam.name}_Q{question['question_idx_in_exam'] + 1}"
                    grade = student['grades'][question['global_question_idx']] if question['global_question_idx'] < len(student['grades']) else 0
                    row[question_name] = grade
            
            # Sınav toplamı
            exam_total = student.get('exam_totals', [])[exam_idx] if exam_idx < len(student.get('exam_totals', [])) else 0
            row[f"{exam.name}_Total"] = exam_total
        
        # Genel toplam
        row['Overall Total'] = student.get('overall_total', 0)
        student_grades_data.append(row)
    
    # 2. İstatistikler Tablosu
    stats_data = []
    for exam_idx, exam in enumerate(exams):
        for question in all_questions_flat:
            if question['exam_idx'] == exam_idx:
                stat = stats[question['global_question_idx']] if question['global_question_idx'] < len(stats) else {}
                row = {
                    'Exam': exam.name,
                    'Question': f"Q{question['question_idx_in_exam'] + 1}",
                    'Max Points': question['max_points'],
                    'Average': stat.get('avg', 0),
                    'Median': stat.get('median', 0),
                    'Max': stat.get('max', 0),
                    'Min': stat.get('min', 0),
                    'Performance Median (%)': stat.get('performance_median', 0)
                }
                stats_data.append(row)
    
    # 3. CLO Analiz Sonuçları
    clo_analysis_data = []
    for clo_idx in range(len(clo_results)):
        # Normalized CLO değerini doğrudan clo_results'dan al
        normalized_clo = clo_results[clo_idx].get('normalized_clo_score', 0)
        avg_bloom_level = clo_results[clo_idx].get('average_bloom_score', 0)
        
        # Performance ve recommendation belirleme
        if normalized_clo >= 85 and avg_bloom_level > 3.0:
            performance_text = "Excellent mastery with deep, higher-order thinking"
            recommendation_text = "Maintain teaching and assessment strategy; consider sharing as best practice"
        elif normalized_clo >= 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Excellent mastery, but mostly mid-level cognitive tasks"
            recommendation_text = "Improve assessment depth (add BL 4 questions) while retaining core approach"
        elif normalized_clo >= 85 and avg_bloom_level < 2:
            performance_text = "Superficial mastery — strong scores from low-level tasks"
            recommendation_text = "Replace low-level assessments with tasks that demand higher-order thinking"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level > 3.0:
            performance_text = "Strong achievement with rich cognitive engagement"
            recommendation_text = "Maintain rigor; consider refining support strategies for students"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Strong results with balanced cognitive challenge"
            recommendation_text = "Introduce more Bloom Level 3+ tasks to push students beyond procedural skills"
        elif normalized_clo >= 70 and normalized_clo < 85 and avg_bloom_level < 2:
            performance_text = "Strong scores with limited depth — risk of over-simplification"
            recommendation_text = "Shift from recall-based to application/analysis-type questions"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level > 3.0:
            performance_text = "Moderate learning with challenging conditions"
            recommendation_text = "Offer better scaffolding and conceptual clarity to help students succeed"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Moderate achievement with routine or procedural learning"
            recommendation_text = "Revise both instruction and question difficulty for alignment"
        elif normalized_clo >= 50 and normalized_clo < 70 and avg_bloom_level < 2:
            performance_text = "Basic understanding with very limited thinking depth"
            recommendation_text = "Redesign instruction and assessments to encourage deep learning"
        elif normalized_clo < 50 and avg_bloom_level > 3.0:
            performance_text = "Poor achievement on cognitively rich tasks"
            recommendation_text = "Strengthen foundational teaching and reinforce cognitive scaffolding"
        elif normalized_clo < 50 and avg_bloom_level >= 2 and avg_bloom_level <= 3:
            performance_text = "Low achievement with moderate-level assessment"
            recommendation_text = "Increase student support; revisit topic sequencing, and practice opportunities"
        elif normalized_clo < 50 and avg_bloom_level < 2:
            performance_text = "Critical learning failure — performance and rigor are both weak"
            recommendation_text = "Full instructional and assessment redesign needed — priority for improvement"
        else:
            performance_text = "No data available for assessment"
            recommendation_text = "Please ensure all data is properly entered"
        
        clo_analysis_data.append({
            'CLO': clo_names[clo_idx] if clo_idx < len(clo_names) else f'CLO {clo_idx + 1}',
            'Normalized CLO %': f"{normalized_clo:.2f}%",
            'Average Bloom Level-CLO': f"{avg_bloom_level:.2f}",
            'Student Performance Assessment': performance_text,
            'Recommended Instructor Action': recommendation_text
        })
    
    # Tüm verileri birleştir
    all_data = {
        'Student Grades': student_grades_data,
        'Statistics': stats_data,
        'CLO Analysis': clo_analysis_data
    }
    
    # Excel dosyası oluştur (birden fazla sheet ile)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Her tablo için ayrı sheet
        for sheet_name, data in all_data.items():
            if data:  # Boş değilse
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    
    # Response oluştur
    response = make_response(output.getvalue())
    course_code = course.course_code
    response.headers["Content-Disposition"] = f"attachment; filename={course_code}_all_tables.xlsx"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return response

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

def normalized_clo_score(qct_list, w_list, spm_list):
    """Normalize edilmiş CLO skoru hesapla - yüzde olarak"""
    if not qct_list or not w_list or not spm_list or len(qct_list) != len(w_list) or len(w_list) != len(spm_list):
        print(f"normalized_clo_score: Invalid input lengths - qct:{len(qct_list)}, w:{len(w_list)}, spm:{len(spm_list)}")
        return 0
    
    print(f"normalized_clo_score: Input data - qct_list: {qct_list}, w_list: {w_list}, spm_list: {spm_list}")
    
    # Sadece pozitif değerleri olan soruları al
    valid_data = [(qct, w, spm) for qct, w, spm in zip(qct_list, w_list, spm_list) if qct > 0 and w > 0]
    
    print(f"normalized_clo_score: valid_data = {valid_data}")
    
    if not valid_data:
        print("normalized_clo_score: No valid data found - all qct or w values are 0 or negative")
        return 0
    
    # Normalized CLO Score = (Weighted CLO Score / Max Possible CLO Score) * 100
    weighted_score = sum((qct / 100) * w * (spm / 100) for qct, w, spm in valid_data)
    max_score = sum((qct / 100) * w for qct, w, _ in valid_data)
    
    print(f"normalized_clo_score: weighted_score = {weighted_score}, max_score = {max_score}")
    
    if max_score > 0:
        result = (weighted_score / max_score) * 100
        print(f"normalized_clo_score: result = {result}")
        return result
    else:
        print("normalized_clo_score: max_score is 0 - this should not happen with valid data")
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
                    if grade_idx < len(exam.questions):
                        question = exam.questions[grade_idx]
                        
                        # Mevcut notu bul veya yeni oluştur
                        existing_grade = Grade.query.filter_by(student_id=student.id, question_id=question.id).first()
                        if existing_grade:
                            existing_grade.grade = grade_value
                        else:
                            new_grade = Grade(student_id=student.id, question_id=question.id, grade=grade_value)
                            db.session.add(new_grade)
        
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
    app.run(port=8080, debug=True)
    
    
    
    
