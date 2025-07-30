from flask import Flask, render_template, request, redirect, url_for, session
import numpy as np 

app = Flask(__name__)
app.secret_key = "cok_guclu_bir_gizli_anahtar_buraya_yazilacak_mutlaka_degistirin" 
# ROUTES
@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        exam_count = int(request.form["exam_count"])
        student_count = int(request.form["student_count"])
        session["exam_count"] = exam_count
        session["student_count"] = student_count
        session.pop("exams", None) 
        session.pop("question_points", None)
        session.pop("clos", None) 
        session.pop("students", None)
        session.pop("clo_q_data", None)
        session.pop("clo_results", None)
        session.pop("total_clo_results", None)
        return redirect(url_for("exam_details"))
    return render_template("main.html")

@app.route("/exam_details", methods=["GET", "POST"])
def exam_details():
    exam_count = session.get("exam_count")
    if not exam_count:
        return redirect(url_for("main"))
    
    if request.method == "POST":
        exams = []
        for i in range(exam_count):
            exams.append({
                "name": request.form[f"exam_name_{i}"],
                "question_count": int(request.form[f"question_count_{i}"]),
                "weight": int(request.form[f"weight_{i}"])
            })
        session["exams"] = exams
        return redirect(url_for("question_points"))

    return render_template("exam_details.html", exam_count=exam_count, enumerate=enumerate)

@app.route("/question_points", methods=["GET", "POST"])
def question_points():
    exams = session.get("exams")
    if not exams:
        return redirect(url_for("exam_details"))
    
    if request.method == "POST":
        question_points_list = []
        for idx, exam in enumerate(exams):
            points = []
            for q in range(int(exam["question_count"])):
                key = f"points_{idx}_{q}"
                points.append(float(request.form.get(key, 0))) 
            question_points_list.append(points)
        session["question_points"] = question_points_list
        return redirect(url_for("clo_details"))

    return render_template("question_points.html", exams=exams, enumerate=enumerate)

@app.route("/clo_details", methods=["GET", "POST"])
def clo_details():
    if request.method == "POST":
        clo_count = int(request.form.get("clo_count", 0))
        clos = []
        for i in range(clo_count):
            clos.append({
                "name": request.form[f"clo_name_{i}"]
            })
        session["clos"] = clos
        return redirect(url_for("student_grades"))
    
    clo_count_from_session = session.get("clos")
    if clo_count_from_session is not None:
        clo_count = len(clo_count_from_session)
    else:
        clo_count = 1 

    return render_template("clo_details.html", clo_count=clo_count, enumerate=enumerate)

@app.route("/bloom_level_mapping", methods=["GET", "POST"])
def bloom_level_mapping():
    exams = session.get("exams")
    clos = session.get("clos")
    students_data = session.get("students", []) 
    question_points_nested = session.get("question_points")
    student_count = session.get("student_count") 

    if not exams or not clos or not question_points_nested:
        # Eğer gerekli oturum verileri yoksa, başlangıç sayfasına yönlendir
        return redirect(url_for("main"))

    all_questions_flat = []
    global_q_idx_counter = 0
    all_questions_flat_map = {} 
    for exam_idx, exam in enumerate(exams):
        all_questions_flat_map[exam_idx] = {}
        for q_idx_in_exam in range(int(exam['question_count'])):
            max_points = 0
            if question_points_nested and len(question_points_nested) > exam_idx and \
               len(question_points_nested[exam_idx]) > q_idx_in_exam:
                max_points = question_points_nested[exam_idx][q_idx_in_exam]

            all_questions_flat.append({
                'exam_idx': exam_idx,
                'question_idx_in_exam': q_idx_in_exam,
                'global_question_idx': global_q_idx_counter,
                'max_points': max_points
            })
            all_questions_flat_map[exam_idx][q_idx_in_exam] = global_q_idx_counter
            global_q_idx_counter += 1

    # clo_q_data'yı oturumdan çek, yoksa boş bir sözlük olarak başlat
    clo_q_data = session.get("clo_q_data", {})

    # GET isteğinde veya ilk yüklemede SPM değerlerini ve varsayılan boş string değerlerini ayarla
    for clo_idx, clo in enumerate(clos):
        if clo_idx not in clo_q_data:
            clo_q_data[clo_idx] = {}
        for q_flat in all_questions_flat:
            global_q_idx = q_flat['global_question_idx']
            
            grades_for_q = []
            for student in students_data:
                # `student`'ın bir dict olduğunu ve 'grades' key'inin varlığını kontrol et
                if isinstance(student, dict) and student.get('grades') and global_q_idx < len(student['grades']):
                    grade = student['grades'][global_q_idx]
                    if grade is not None:
                        grades_for_q.append(grade)
            
            spm_value = 0
            if grades_for_q and q_flat['max_points'] > 0:
                # NumPy'nin median fonksiyonunu kullanmak için liste boş değilse
                if len(grades_for_q) > 0:
                    median_grade = float(np.median(grades_for_q))
                    spm_value = (median_grade / q_flat['max_points']) * 100
                else:
                    spm_value = 0 # If no grades, SPM is 0

            if global_q_idx not in clo_q_data[clo_idx]:
                clo_q_data[clo_idx][global_q_idx] = {}
            
            clo_q_data[clo_idx][global_q_idx]['spm'] = round(spm_value, 2)
            
            # İlk yüklemede (GET request) veya değerler zaten POST ile gelmemişse
            # input alanlarının boş string olarak başlamasını sağla.
            # float(None) hatasını engellemek için None yerine '' atıyoruz.
            if request.method == "GET":
                if 'qct' not in clo_q_data[clo_idx][global_q_idx] or clo_q_data[clo_idx][global_q_idx]['qct'] is None:
                    clo_q_data[clo_idx][global_q_idx]['qct'] = ''
                if 'w' not in clo_q_data[clo_idx][global_q_idx] or clo_q_data[clo_idx][global_q_idx]['w'] is None:
                    clo_q_data[clo_idx][global_q_idx]['w'] = ''
                if 'bl' not in clo_q_data[clo_idx][global_q_idx] or clo_q_data[clo_idx][global_q_idx]['bl'] is None:
                    clo_q_data[clo_idx][global_q_idx]['bl'] = ''

    # POST isteği geldiğinde form verilerini işle
    if request.method == "POST":
        for clo_idx, clo in enumerate(clos):
            if clo_idx not in clo_q_data:
                clo_q_data[clo_idx] = {}
            for q_flat in all_questions_flat:
                global_q_idx = q_flat['global_question_idx']
                qct_val = request.form.get(f"qct_{clo_idx}_{global_q_idx}")
                w_val = request.form.get(f"w_{clo_idx}_{global_q_idx}")
                bl_val = request.form.get(f"bl_{clo_idx}_{global_q_idx}")
                
                # Değerleri float'a çevir, boşsa None olarak sakla
                clo_q_data[clo_idx][global_q_idx]['qct'] = float(qct_val) if qct_val else None
                clo_q_data[clo_idx][global_q_idx]['w'] = float(w_val) if w_val else None
                clo_q_data[clo_idx][global_q_idx]['bl'] = float(bl_val) if bl_val else None
        
        session["clo_q_data"] = clo_q_data 
        
    # Hesaplamaları yap
    clo_results = {}
    total_clo_results = {
        'total_max_clo_score': 0,
        'total_weighted_clo_score': 0,
        'total_normalized_clo_score': 0,
        'total_max_bloom_score': 0,
        'total_weighted_bloom_score': 0,
        'total_average_bloom_score': 0
    }
    
    for clo_idx, clo in enumerate(clos):
        max_clo_score = 0.0
        weighted_clo_score = 0.0
        max_bloom_score = 0.0
        weighted_bloom_score = 0.0
        
        for q_flat in all_questions_flat:
            global_q_idx = q_flat['global_question_idx']
            q_data = clo_q_data.get(clo_idx, {}).get(global_q_idx, {})
            
            # Değerleri float'a çevir, yoksa 0 olarak varsay
            qct = float(q_data.get('qct') or 0.0)
            w = float(q_data.get('w') or 0.0)
            bl = float(q_data.get('bl') or 0.0)
            spm = float(q_data.get('spm') or 0.0)

            max_clo_score += (qct / 100.0) * w
            weighted_clo_score += (qct / 100.0) * w * spm
            max_bloom_score += (qct / 100.0) * w * bl
            weighted_bloom_score += (qct / 100.0) * w * bl

        normalized_clo_score = (weighted_clo_score / max_clo_score) if max_clo_score > 0 else 0.0
        average_bloom_score = (weighted_bloom_score / max_clo_score) if max_clo_score > 0 else 0.0

        clo_results[clo_idx] = {
            'max_clo_score': max_clo_score,
            'weighted_clo_score': weighted_clo_score,
            'normalized_clo_score': normalized_clo_score,
            'max_bloom_score': max_bloom_score,
            'weighted_bloom_score': weighted_bloom_score,
            'average_bloom_score': average_bloom_score
        }

        total_clo_results['total_max_clo_score'] += max_clo_score
        total_clo_results['total_weighted_clo_score'] += weighted_clo_score
        total_clo_results['total_normalized_clo_score'] += normalized_clo_score
        total_clo_results['total_max_bloom_score'] += max_bloom_score
        total_clo_results['total_weighted_bloom_score'] += weighted_bloom_score
        total_clo_results['total_average_bloom_score'] += average_bloom_score
    
    session["clo_results"] = clo_results
    session["total_clo_results"] = total_clo_results

    return render_template(
        "bloom_mapping.html",
        exams=exams,
        clos=clos,
        all_questions_flat=all_questions_flat,
        all_questions_flat_map=all_questions_flat_map,
        clo_q_data=clo_q_data,
        clo_results=clo_results,
        total_clo_results=total_clo_results,
        students_data=students_data,
        student_count=student_count,
        enumerate=enumerate
    )

@app.route("/student_grades", methods=["GET", "POST"])
def student_grades():
    exams = session.get("exams")
    student_count = session.get("student_count")
    question_points_nested = session.get("question_points")
    clos = session.get("clos") 
    
    if not exams or not student_count or not question_points_nested or not clos:
        return redirect(url_for("main"))
    
    all_questions_flat_for_jinja = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        for q_idx_in_exam in range(int(exam['question_count'])):
            max_points = 0
            if question_points_nested and len(question_points_nested) > exam_idx and \
               len(question_points_nested[exam_idx]) > q_idx_in_exam:
                max_points = question_points_nested[exam_idx][q_idx_in_exam]

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
    # Bu döngü, students_data listesinin her zaman student_count boyutunda olmasını sağlar
    # ve mevcut öğrenci verilerini korurken eksik olanları boş bir dict ile doldurur.
    current_students_data_length = len(students_data)
    if current_students_data_length < student_count:
        for i in range(current_students_data_length, student_count):
            students_data.append({
                "number": "",
                "name": "",
                "grades": [0.0] * len(all_questions_flat_for_jinja),
                "total": 0.0
            })
    elif current_students_data_length > student_count:
        students_data = students_data[:student_count]


    if request.method == "POST":
        students = []
        total_questions_count = len(all_questions_flat_for_jinja)

        for student_idx in range(int(student_count)):
            # Önceki verileri korumak için, eğer öğrenci zaten varsa mevcut verilerini kullan
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
        return redirect(url_for("summary"))

    return render_template("student_grades.html", 
                            exams=exams, 
                            student_count=int(student_count),
                            question_points_nested=question_points_nested, 
                            students_data=students_data, 
                            all_questions_flat=all_questions_flat_for_jinja, 
                            enumerate=enumerate,
                            clos=clos)

@app.route("/summary")
def summary():
    exam_count = session.get("exam_count")
    student_count = session.get("student_count")
    exams = session.get("exams")
    question_points = session.get("question_points")
    students = session.get("students")
    clos = session.get("clos") 

    return render_template("summary.html", 
                            exam_count=exam_count, 
                            student_count=student_count, 
                            exams=exams, 
                            question_points=question_points,
                            students=students,
                            clos=clos,
                            enumerate=enumerate) 

if __name__ == "__main__":
    app.run(port=8080, debug=True)
