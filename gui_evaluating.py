from flask import Flask, render_template, request, redirect, url_for, session, make_response
import pandas as pd
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
        return redirect(url_for("student_grades"))  # Buradan student_grades'e yönlendir

    clo_count_from_session = session.get("clos")
    if clo_count_from_session is not None:
        clo_count = len(clo_count_from_session)
    else:
        clo_count = 1 

    return render_template("clo_details.html", clo_count=clo_count, enumerate=enumerate)
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
        return redirect(url_for("summary"))

    return render_template("student_grades.html", 
                            exams=exams, 
                            student_count=int(student_count),
                            question_points_nested=question_points_nested, 
                            students_data=students_data, 
                            all_questions_flat=all_questions_flat_for_jinja, 
                            enumerate=enumerate,
                            clos=clos)

@app.route("/bloom_level_mapping", methods=["GET", "POST"])
def bloom_level_mapping():
    exams = session.get("exams", [])
    clos = session.get("clos", [])
    question_points_nested = session.get("question_points", [])

    # Tüm soruların global indexlerini oluştur
    all_questions_flat_map = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        exam_map = []
        for q_idx_in_exam in range(int(exam['question_count'])):
            exam_map.append(global_q_idx_counter)
            global_q_idx_counter += 1
        all_questions_flat_map.append(exam_map)

    # Varsayılan değerlerle başlat
    clo_q_data = session.get("clo_q_data", [])
    clo_results = session.get("clo_results", [])
    total_clo_results = session.get("total_clo_results", {})

    if request.method == "POST":
        # Formdan gelen verileri işle
        clo_q_data = []
        for clo_idx in range(len(clos)):
            clo_row = {}
            for exam_idx, exam in enumerate(exams):
                for q in range(exam["question_count"]):
                    global_q_idx = all_questions_flat_map[exam_idx][q]
                    
                    qct_val = request.form.get(f"qct_{clo_idx}_{global_q_idx}")
                    w_val = request.form.get(f"w_{clo_idx}_{global_q_idx}")
                    spm_val = request.form.get(f"spm_{clo_idx}_{global_q_idx}")
                    bl_val = request.form.get(f"bl_{clo_idx}_{global_q_idx}")

                    qct = float(qct_val.strip()) if qct_val and qct_val.strip() else 0.0
                    w = float(w_val.strip()) if w_val and w_val.strip() else 0.0
                    spm = float(spm_val.strip()) if spm_val and spm_val.strip() else 0.0
                    bl = float(bl_val.strip()) if bl_val and bl_val.strip() else 0.0
                    clo_row[global_q_idx] = {"qct": qct, "w": w, "spm": spm, "bl": bl}
            clo_q_data.append(clo_row)

        # Her CLO için hesaplamaları yap
        clo_results = []
        for clo_idx, clo in enumerate(clos):
            qct_list, w_list, spm_list, bl_list = [], [], [], []
            for exam_idx, exam in enumerate(exams):
                for q in range(exam["question_count"]):
                    global_q_idx = all_questions_flat_map[exam_idx][q]
                    qct = clo_q_data[clo_idx][global_q_idx]['qct']
                    w = clo_q_data[clo_idx][global_q_idx]['w']
                    spm = clo_q_data[clo_idx][global_q_idx]['spm']
                    bl = clo_q_data[clo_idx][global_q_idx]['bl']
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

        # Toplam değerleri hesapla
        total_clo_results = {
            "total_max_clo_score": sum(r["max_clo_score"] for r in clo_results),
            "total_weighted_clo_score": sum(r["weighted_clo_score"] for r in clo_results),
            "total_normalized_clo_score": sum(r["normalized_clo_score"] for r in clo_results),
            "total_average_bloom_score": sum(r["average_bloom_score"] for r in clo_results),
            "total_weighted_bloom_score": sum(r["weighted_bloom_score"] for r in clo_results)
        }

        # Session'a kaydet
        session["clo_q_data"] = clo_q_data
        session["clo_results"] = clo_results
        session["total_clo_results"] = total_clo_results

    return render_template(
        "bloom_mapping.html",
        exams=exams,
        clos=clos,
        all_questions_flat_map=all_questions_flat_map,
        clo_q_data=clo_q_data,
        clo_results=clo_results,
        total_clo_results=total_clo_results,
        enumerate=enumerate
    )

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

@app.route("/download_csv")
def download_csv():
    students_data = session.get('students', [])
    exams = session.get('exams', [])
    question_points_nested = session.get('question_points', [])
    
    if not students_data:
        return "Öğrenci verisi bulunamadı.", 404
        
    all_questions_flat = []
    for exam in exams:
        for q in range(int(exam['question_count'])):
            all_questions_flat.append(f"Q_{exam['name']}_{q+1}")
            
    df_data = []
    for student in students_data:
        row = {
            "Öğrenci No": student.get("number", ""),
            "Ad-Soyad": student.get("name", "")
        }
        for i, grade in enumerate(student.get("grades", [])):
            if i < len(all_questions_flat):
                row[all_questions_flat[i]] = grade
        row["Toplam Not"] = student.get("total", 0.0)
        df_data.append(row)
        
    df = pd.DataFrame(df_data)

    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
    bom = '\ufeff'
    csv_output = bom + output.getvalue()

    response = make_response(csv_output)
    response.headers["Content-Disposition"] = "attachment; filename=student_grades.csv"
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
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
    bom = '\ufeff'
    csv_output = bom + output.getvalue()

    response = make_response(csv_output)
    response.headers["Content-Disposition"] = "attachment; filename=clo_details.csv"
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
    # MW-BL'nin, Max CLO Score ile aynı formülle hesaplanması isteniyorsa,
    # bl listesini dikkate almayıp bu formülü kullanın.
    return sum((qct / 100) * w for qct, w in zip(qct_list, w_list))

if __name__ == "__main__":
    app.run(port=8080, debug=True)

    
