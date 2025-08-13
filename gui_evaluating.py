from flask import Flask, render_template, request, redirect, url_for, session, make_response
import pandas as pd
import numpy as np
import io 

app = Flask(__name__)
app.secret_key = "your_secret_key_here" 

# ROUTES
@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
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
    exam_count = session.get("exam_count")
    if not exam_count:
        return redirect(url_for("main"))
    
    if request.method == "POST":
        # Process CLO configuration
        clo_count = int(request.form.get("clo_count", 10))
        clo_names = []
        for i in range(clo_count):
            clo_name = request.form.get(f"clo_name_{i}", f"CLO {i+1}")
            clo_names.append(clo_name)
        
        # Store CLO configuration in session
        session["clo_count"] = clo_count
        session["clo_names"] = clo_names
        
        # Process exam details
        exams = []
        for i in range(exam_count):
            exams.append({
                "name": request.form[f"exam_name_{i}"],
                "question_count": int(request.form[f"question_count_{i}"]),
                "weight": int(request.form[f"weight_{i}"])
            })
        session["exams"] = exams
        return redirect(url_for("question_points"))

    # Get existing CLO configuration for display
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    
    return render_template("exam_details.html", 
                         exam_count=exam_count, 
                         clo_count=clo_count,
                         clo_names=clo_names,
                         enumerate=enumerate)

@app.route("/question_points", methods=["GET", "POST"])
def question_points():
    exams = session.get("exams")
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
                qct = float(request.form.get(f"qct_{idx}_{q}", 0))
                bl = float(request.form.get(f"bl_{idx}_{q}", 0))
                n_clo = len(selected_clos)
                w_val = 1.0 / n_clo if n_clo > 0 else 0.0
                for clo in selected_clos:
                    questions.append({
                        "points": points,
                        "clo": clo,
                        "qct": qct,
                        "w": w_val,
                        "bl": bl,
                        "question_idx": q
                    })
            question_points_list.append(questions)
            # Toplamı kontrol et
            if abs(running_sum - 100.0) > 1e-6:
                return f"{exams[idx]['name']} için soru puanları toplamı {running_sum}. Toplam 100 olmalı.", 400
        session["question_points"] = question_points_list
        return redirect(url_for("student_grades"))
    return render_template(
        "question_points.html",
        exams=exams,
        clo_count=clo_count,
        clo_names=clo_names,
        students_per_exam=students_per_exam,
        enumerate=enumerate,
    )

@app.route("/student_grades", methods=["GET", "POST"])
def student_grades():
    exams = session.get("exams")
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

    # students_data'yı boş listeyle başlat veya oturumdan çek
    students_data = session.get('students', [])
    
    # students_data'nın öğrenci sayısı kadar boş veya mevcut öğrenci nesneleri içermesini sağla
    current_students_data_length = len(students_data)
    if current_students_data_length < student_count:
        for i in range(current_students_data_length, student_count):
            students_data.append({
                "number": "",
                "name": "",
                "grades": [''] * len(all_questions_flat_for_jinja),
                "total": 0.0
            })
    elif current_students_data_length > student_count:
        students_data = students_data[:student_count]

    if request.method == "POST":
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

            students.append({
                "number": student_number,
                "name": student_name,
                "grades": student_grades_list, 
                "total": round(current_student_total_score, 1) 
            })
        
        session["students"] = students
        # yeni eklenen satır burada
        session["question_points"] = question_points_nested
        return redirect(url_for("summary"))

    session["all_questions_flat"] = all_questions_flat_for_jinja 
    return render_template("student_grades.html", 
                            exams=exams, 
                            student_count=int(student_count),
                            question_points_nested=question_points_nested, 
                            students_data=students_data, 
                            all_questions_flat=all_questions_flat_for_jinja, 
                            students_per_exam=students_per_exam,
                            enumerate=enumerate)

@app.route("/bloom_level_mapping", methods=["GET", "POST"])
def bloom_level_mapping():
    exams = session.get("exams", [])
    question_points_nested = session.get("question_points", [])
    clo_count = session.get("clo_count", 10)
    clo_names = session.get("clo_names", [f"CLO {i+1}" for i in range(clo_count)])
    
    if request.method == "POST":
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
        
        clo_table_data = []
        for clo_idx in range(1, clo_count+1):
            row = {
                'CLO': clo_names[clo_idx-1] if clo_idx-1 < len(clo_names) else f'CLO {clo_idx}',
                'Max CLO Score': clo_results[clo_idx-1]['max_clo_score'],
                'CLO Score': clo_results[clo_idx-1]['weighted_clo_score'],
                'MW-BL': clo_results[clo_idx-1]['average_bloom_score'],
                'Weighted BL Sum': clo_results[clo_idx-1]['weighted_bloom_score']
            }
            clo_table_data.append(row)
        session['clo_table'] = clo_table_data
        
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
        
        # POST/Redirect/GET pattern - form gönderildikten sonra GET ile yönlendir
        return redirect(url_for("bloom_level_mapping"))
    
    # GET request - sayfayı göster
    all_questions_flat_map = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        exam_map = []
        for q_idx_in_exam in range(int(exam['question_count'])):
            exam_map.append(global_q_idx_counter)
            global_q_idx_counter += 1
        all_questions_flat_map.append(exam_map)
    
    question_performance_medians = session.get("question_performance_medians", [])
    clo_q_data = session.get("clo_q_data", [])
    
    # Eğer clo_q_data boşsa, varsayılan değerlerle doldur
    if not clo_q_data:
        clo_q_data = []
        global_q_idx_counter = 0
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
                        
                        clo_row[global_q_idx_counter] = {
                            'qct': rec.get('qct', 0.0),
                            'w': rec.get('w', 0.0),
                            'spm': spm_val,
                            'bl': rec.get('bl', 0.0),
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
    
    # Hesaplamaları yap
    clo_results = session.get("clo_results", [])
    total_clo_results = session.get("total_clo_results", {})
    
    if not clo_results:
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
    
    return render_template(
        "bloom_mapping.html",
        exams=exams,
        clos=list(range(1, clo_count+1)),
        clo_names=clo_names,
        all_questions_flat_map=all_questions_flat_map,
        clo_q_data=clo_q_data,
        clo_results=clo_results,
        total_clo_results=total_clo_results,
        enumerate=enumerate
    )

# ... (Diğer fonksiyonlar) ...

@app.route("/summary")
def summary():
    exams = session.get("exams")
    students = session.get("students")
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
            # Güvenli erişim için kontrol ekle
            if (exam_idx < len(question_points) and 
                q_idx_in_exam < len(question_points[exam_idx]) and 
                question_points[exam_idx][q_idx_in_exam] is not None):
                max_points = question_points[exam_idx][q_idx_in_exam]['points'] if isinstance(question_points[exam_idx][q_idx_in_exam], dict) else question_points[exam_idx][q_idx_in_exam]
        else:
            max_points = 0  # Varsayılan değer
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
        enumerate=enumerate
    )

@app.route("/download_csv/<int:exam_index>", methods=["POST"])
def download_csv(exam_index):
    exams = session.get('exams', [])
    all_questions_flat = session.get('all_questions_flat', [])
    student_count = session.get("student_count")

    if not exams or not all_questions_flat:
        return "Gerekli veriler oturumda bulunamadı.", 400

    exam_name = exams[exam_index]['name']
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
    response.headers["Content-Disposition"] = f"attachment; filename={exam_name.replace(' ', '_')}_notlari.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

@app.route("/download_clo_csv")
def download_clo_csv():
    clo_table = session.get('clo_table', [])
    
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
    response.headers["Content-Disposition"] = "attachment; filename=clo_details.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

@app.route("/download_clo_analysis_csv")
def download_clo_analysis_csv():
    clo_results = session.get('clo_results', [])
    clo_names = session.get('clo_names', [])
    
    if not clo_results:
        return "CLO Analysis verisi bulunamadı.", 404
    
    # CLO Analysis Results tablosu için veri hazırla
    analysis_data = []
    for clo_idx in range(len(clo_results)):
        normalized_clo = ((clo_results[clo_idx]['weighted_clo_score'] / clo_results[clo_idx]['max_clo_score']) * 100) if clo_results[clo_idx]['max_clo_score'] > 0 else 0
        # Average Bloom Level-CLO hesaplaması düzeltildi
        avg_bloom_level = clo_results[clo_idx]['average_bloom_score'] if clo_results[clo_idx]['average_bloom_score'] > 0 else 0
        
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
    response.headers["Content-Disposition"] = "attachment; filename=clo_analysis_results.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8-sig"

    return response

# CALCULATION FUNCTIONS
def max_possible_clo_score(qct_list, w_list):
    return sum((qct / 100) * w for qct, w in zip(qct_list, w_list))

def weighted_clo_score(qct_list, w_list, spm_list):
    return sum((qct / 100) * w * (spm / 100) for qct, w, spm in zip(qct_list, w_list, spm_list))

def normalized_clo_score(qct_list, w_list, spm_list):
    numerator = sum((qct / 100) * w * spm for qct, w, spm in zip(qct_list, w_list, spm_list))
    denominator = sum((qct / 100) * w for qct, w in zip(qct_list, w_list))
    return numerator / denominator if denominator != 0 else 0

def weighted_bloom_score(qct_list, w_list, bl_list):
    return sum((qct / 100) * w * bl for qct, w, bl in zip(qct_list, w_list, bl_list))

def average_bloom_score(qct_list, w_list, bl_list):
    # Weighted BL Sum ÷ MW-BL hesaplaması
    weighted_bloom_sum = sum((qct / 100) * w * bl for qct, w, bl in zip(qct_list, w_list, bl_list))
    mw_bl = sum((qct / 100) * w for qct, w in zip(qct_list, w_list))
    return weighted_bloom_sum / mw_bl if mw_bl > 0 else 0

if __name__ == "__main__":
    app.run(port=8080, debug=True)
    
    
    
    
