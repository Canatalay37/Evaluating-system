from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "gizli_anahtar"

main_page = """
<!doctype html>
<html>
<head>
<title>Start</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
form { background: #f5f5f5; padding: 20px; border-radius: 8px; max-width: 400px; }
input[type="number"] { padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
input[type="submit"] { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
input[type="submit"]:hover { background: #0056b3; }
</style>
</head>
<body>
<h2>Sınav Değerlendirme Sistemi</h2>
<form method="post">
  <label>Kaç sınav var? <input type="number" name="exam_count" min="1" max="10" value="1" required></label><br><br>
  <label>Kaç öğrenci var? <input type="number" name="student_count" min="1" max="100" required></label><br><br>
  <input type="submit" value="Devam Et">
</form>
</body>
</html>
"""

exam_details_page = """
<!doctype html>
<html>
<head>
<title>Exam Details</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
form { background: #f5f5f5; padding: 20px; border-radius: 8px; max-width: 600px; }
input[type="text"], input[type="number"] { padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
input[type="submit"] { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
.exam-section { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #ddd; }
</style>
</head>
<body>
<h2>Sınav Detayları</h2>
<form method="post">
  {% for i in range(exam_count) %}
    <div class="exam-section">
      <h3>Sınav {{ i+1 }}</h3>
      <label>Sınav Adı: <input type="text" name="exam_name_{{i}}" placeholder="Örn: Vize Sınavı" required></label><br>
      <label>Soru Sayısı: <input type="number" name="question_count_{{i}}" min="1" max="50" required></label><br>
      <label>Ağırlık (%): <input type="number" name="weight_{{i}}" min="1" max="100" required></label><br>
    </div>
  {% endfor %}
  <input type="submit" value="Kaydet ve Devam Et">
</form>
</body>
</html>
"""

question_points_page = """
<!doctype html>
<html>
<head>
<title>Question Points</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
form { background: #f5f5f5; padding: 20px; border-radius: 8px; }
input[type="number"] { padding: 8px; margin: 2px; border: 1px solid #ddd; border-radius: 4px; width: 80px; }
input[type="submit"] { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-top: 20px; }
.exam-section { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #ddd; }
.question-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
</style>
</head>
<body>
<h2>Her Soru İçin Puan Girin</h2>
<form method="post">
  {% for exam in exams %}
    <div class="exam-section">
      <h3>{{ exam['name'] }}</h3>
      <div class="question-grid">
        {% for q in range(exam['question_count']|int) %}
          <label>Soru {{ q+1 }}: <input type="number" name="points_{{loop.index0}}_{{q}}" min="0" max="100" required></label>
        {% endfor %}
      </div>
    </div>
  {% endfor %}
  <input type="submit" value="Kaydet ve Devam Et">
</form>
</body>
</html>
"""

student_grades_page = """
<!doctype html>
<html>
<head>
<title>Student Grades</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; font-size: 12px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #333; padding: 3px; text-align: center; vertical-align: middle; }
th { background-color: #f0f0f0; font-weight: bold; font-size: 11px; }
input[type="text"], input[type="number"] { 
  width: 100%; 
  border: none; 
  text-align: center; 
  padding: 2px; 
  font-size: 11px;
  box-sizing: border-box;
}
input[readonly] { 
  background-color: #f8f9fa; 
  color: #333;
}
.student-row { background-color: white; }
.stats-row { background-color: #e6f3ff; }
.total-points-row { background-color: #ffff99; font-weight: bold; }
.exam-contribution-row { background-color: #90EE90; }
.question-contribution-row { background-color: #90EE90; }
.performance-row { background-color: #FFA500; color: #d63031; font-weight: bold; }
.submit-btn { 
  background: #007bff; 
  color: white; 
  padding: 10px 20px; 
  border: none; 
  border-radius: 4px; 
  cursor: pointer; 
  margin-top: 20px; 
}
.id-col { width: 30px; }
.student-info-col { width: 120px; }
.question-col { width: 45px; }
.total-col { width: 60px; }
</style>
</head>
<body>
<h2>Öğrenci Bilgileri ve Not Girişi</h2>

{% set question_points = session.get('question_points', []) %}
{% set all_questions = [] %}

{% for exam_idx, exam in enumerate(exams) %}
  {% for q_idx in range(exam.question_count|int) %}
    {% set _ = all_questions.append({
      'exam_idx': exam_idx,
      'question_idx': q_idx,
      'max_points': question_points[exam_idx][q_idx]|int if question_points and question_points[exam_idx] else 10,
      'question_number': all_questions|length + 1
    }) %}
  {% endfor %}
{% endfor %}

<form method='post'>
  <table>
    <thead>
      <tr>
        <th class="id-col">ID</th>
        <th class="student-info-col">Öğrenci No</th>
        <th class="student-info-col">Ad-Soyad</th>
        {% for question in all_questions %}
          <th class="question-col">Q{{ question.question_number }}</th>
        {% endfor %}
        <th class="total-col">Toplam</th>
      </tr>
    </thead>
    <tbody>
      {% for student_idx in range(student_count) %}
        <tr class="student-row">
          <td>{{ student_idx + 1 }}</td>
          <td><input type="text" name="student_number_{{ student_idx }}" placeholder="Öğr. No" style="width:95%;"></td>
          <td><input type="text" name="student_name_{{ student_idx }}" placeholder="Ad Soyad" style="width:95%;"></td>
          {% for q_idx in range(all_questions|length) %}
            <td>
              <input type="number" 
                     class="grade-input" 
                     name="grade_{{ student_idx }}_{{ q_idx }}" 
                     min="0" 
                     max="{{ all_questions[q_idx].max_points }}" 
                     step="0.5"
                     data-student="{{ student_idx }}" 
                     data-question="{{ q_idx }}"
                     style="width:40px;">
            </td>
          {% endfor %}
          <td><input type="text" class="total-input" name="total_{{ student_idx }}" readonly style="width:50px;"></td>
        </tr>
      {% endfor %}
    </tbody>
    <tfoot>
      <!-- Max satırı -->
      <tr class="stats-row">
        <th>Max</th>
        <td colspan="2"></td>
        {% for q_idx in range(all_questions|length) %}
          <td><input type="text" class="max-q" data-question="{{ q_idx }}" readonly style="width:40px;"></td>
        {% endfor %}
        <td><input type="text" class="max-total" readonly style="width:50px;"></td>
      </tr>
      
      <!-- Min satırı -->
      <tr class="stats-row">
        <th>Min</th>
        <td colspan="2"></td>
        {% for q_idx in range(all_questions|length) %}
          <td><input type="text" class="min-q" data-question="{{ q_idx }}" readonly style="width:40px;"></td>
        {% endfor %}
        <td><input type="text" class="min-total" readonly style="width:50px;"></td>
      </tr>
      
      <!-- Ortalama satırı -->
      <tr class="stats-row">
        <th>Ortalama</th>
        <td colspan="2"></td>
        {% for q_idx in range(all_questions|length) %}
          <td><input type="text" class="avg-q" data-question="{{ q_idx }}" readonly style="width:40px;"></td>
        {% endfor %}
        <td><input type="text" class="avg-total" readonly style="width:50px;"></td>
      </tr>
      
      <!-- Medyan satırı -->
      <tr class="stats-row">
        <th>Medyan</th>
        <td colspan="2"></td>
        {% for q_idx in range(all_questions|length) %}
          <td><input type="text" class="median-q" data-question="{{ q_idx }}" readonly style="width:40px;"></td>
        {% endfor %}
        <td><input type="text" class="median-total" readonly style="width:50px;"></td>
      </tr>
      
      <!-- Toplam Puanlar -->
      <tr class="total-points-row">
        <th>Toplam</th>
        <td colspan="2"></td>
        {% for question in all_questions %}
          <td>{{ question.max_points }}</td>
        {% endfor %}
        <td>{{ all_questions|sum(attribute='max_points') }}</td>
      </tr>
      
      <!-- Sınav Katkısı -->
      <tr class="exam-contribution-row">
        <th colspan="3">Sınav Katkısı Toplam (%)</th>
        {% for question in all_questions %}
          <td>{{ exams[question.exam_idx].weight }}</td>
        {% endfor %}
        <td>100</td>
      </tr>
      
      <!-- Soru Katkısı -->
      <tr class="question-contribution-row">
        <th colspan="3">Soru Katkısı Toplam (%)</th>
        {% for q_idx in range(all_questions|length) %}
          <td><input type="text" class="question-contribution" data-question="{{ q_idx }}" readonly style="width:40px;"></td>
        {% endfor %}
        <td></td>
      </tr>
      
      <!-- Öğrenci Performans Medyanı -->
      <tr class="performance-row">
        <th colspan="3">Öğrenci Performans Medyanı</th>
        {% for q_idx in range(all_questions|length) %}
          <td><input type="text" class="performance-median" data-question="{{ q_idx }}" readonly style="width:40px;"></td>
        {% endfor %}
        <td><input type="text" class="performance-median-total" readonly style="width:50px;"></td>
      </tr>
    </tfoot>
  </table>
  <br>
  <input type="submit" value="Kaydet ve Özet Görüntüle" class="submit-btn">
</form>

<script>
// Soru puanları dizisi
const questionPoints = [
  {% for question in all_questions %}
    {{ question.max_points }}{% if not loop.last %},{% endif %}
  {% endfor %}
];
const studentCount = {{ student_count }};
const totalPossiblePoints = questionPoints.reduce((a,b) => a+b, 0);

function getColumnValues(colIdx) {
  let vals = [];
  for (let i = 0; i < studentCount; i++) {
    let inp = document.querySelector(`input[name='grade_${i}_${colIdx}']`);
    if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
      vals.push(parseFloat(inp.value));
    }
  }
  return vals;
}

function getTotalValues() {
  let vals = [];
  for (let i = 0; i < studentCount; i++) {
    let inp = document.querySelector(`input[name='total_${i}']`);
    if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
      vals.push(parseFloat(inp.value));
    }
  }
  return vals;
}

function calcStats(arr) {
  if (arr.length === 0) return {max: '', min: '', avg: '', median: ''};
  
  let sorted = [...arr].sort((a,b) => a - b);
  let sum = arr.reduce((a,b) => a + b, 0);
  let avg = sum / arr.length;
  let median = arr.length % 2 === 1 
    ? sorted[Math.floor(arr.length / 2)]
    : (sorted[arr.length / 2 - 1] + sorted[arr.length / 2]) / 2;
    
  return {
    max: Math.max(...arr),
    min: Math.min(...arr) === 0 ? 0 : Math.min(...arr),
    avg: parseFloat(avg.toFixed(1)),
    median: parseFloat(median.toFixed(1))
  };
}

function calculatePerformanceMedian(questionIdx, questionMaxPoints) {
  let vals = getColumnValues(questionIdx);
  if (vals.length === 0) return '';
  
  let performancePercentages = vals.map(val => (val / questionMaxPoints) * 100);
  performancePercentages.sort((a,b) => a - b);
  
  let median = performancePercentages.length % 2 === 1 
    ? performancePercentages[Math.floor(performancePercentages.length / 2)]
    : (performancePercentages[performancePercentages.length / 2 - 1] + performancePercentages[performancePercentages.length / 2]) / 2;
    
  return parseFloat(median.toFixed(2));
}

function recalcAll() {
  const qCount = questionPoints.length;
  
  // Her öğrenci için toplam hesapla
  for (let i = 0; i < studentCount; i++) {
    let total = 0;
    for (let q = 0; q < qCount; q++) {
      let inp = document.querySelector(`input[name='grade_${i}_${q}']`);
      if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
        total += parseFloat(inp.value);
      }
    }
    let totalInput = document.querySelector(`input[name='total_${i}']`);
    if (totalInput) {
      totalInput.value = total > 0 ? total : '';
    }
  }
  
  // Her soru için istatistikler
  for (let q = 0; q < qCount; q++) {
    let vals = getColumnValues(q);
    let stats = calcStats(vals);
    
    // Max, Min, Avg, Median
    let maxInput = document.querySelector(`.max-q[data-question='${q}']`);
    let minInput = document.querySelector(`.min-q[data-question='${q}']`);
    let avgInput = document.querySelector(`.avg-q[data-question='${q}']`);
    let medianInput = document.querySelector(`.median-q[data-question='${q}']`);
    
    if (maxInput) maxInput.value = stats.max;
    if (minInput) minInput.value = stats.min;
    if (avgInput) avgInput.value = stats.avg;
    if (medianInput) medianInput.value = stats.median;
    
    // Soru katkı yüzdesi
    let contributionPercent = ((questionPoints[q] / totalPossiblePoints) * 100).toFixed(0);
    let contribInput = document.querySelector(`.question-contribution[data-question='${q}']`);
    if (contribInput) contribInput.value = contributionPercent;
    
    // Performans medyanı
    let perfMedian = calculatePerformanceMedian(q, questionPoints[q]);
    let perfInput = document.querySelector(`.performance-median[data-question='${q}']`);
    if (perfInput) perfInput.value = perfMedian;
  }
  
  // Toplam sütun istatistikleri
  let totalVals = getTotalValues();
  let tStats = calcStats(totalVals);
  
  let maxTotalInput = document.querySelector('.max-total');
  let minTotalInput = document.querySelector('.min-total');
  let avgTotalInput = document.querySelector('.avg-total');
  let medianTotalInput = document.querySelector('.median-total');
  
  if (maxTotalInput) maxTotalInput.value = tStats.max;
  if (minTotalInput) minTotalInput.value = tStats.min;
  if (avgTotalInput) avgTotalInput.value = tStats.avg;
  if (medianTotalInput) medianTotalInput.value = tStats.median;
  
  // Toplam performans medyanı
  if (totalVals.length > 0) {
    let totalPerformancePercentages = totalVals.map(val => (val / totalPossiblePoints) * 100);
    totalPerformancePercentages.sort((a,b) => a - b);
    let totalPerfMedian = totalPerformancePercentages.length % 2 === 1 
      ? totalPerformancePercentages[Math.floor(totalPerformancePercentages.length / 2)]
      : (totalPerformancePercentages[totalPerformancePercentages.length / 2 - 1] + totalPerformancePercentages[totalPerformancePercentages.length / 2]) / 2;
    
    let perfTotalInput = document.querySelector('.performance-median-total');
    if (perfTotalInput) perfTotalInput.value = parseFloat(totalPerfMedian.toFixed(2));
  }
}

// Event listener'ları ekle
document.addEventListener('DOMContentLoaded', function() {
  // Tüm not girişlerini dinle
  document.querySelectorAll('.grade-input').forEach(function(inp) {
    inp.addEventListener('input', recalcAll);
    inp.addEventListener('change', recalcAll);
  });
  
  // Sayfa yüklendiğinde hesapla
  setTimeout(recalcAll, 100);
});
</script>
</body>
</html>
"""

summary_page = """
<!doctype html>
<html>
<head>
<title>Summary</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
.summary-section { background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 8px; border: 1px solid #dee2e6; }
ul { list-style-type: none; padding: 0; }
li { background: white; margin: 5px 0; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
.back-btn { background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 20px; }
.back-btn:hover { background: #545b62; }
</style>
</head>
<body>
<h2>Sınav Değerlendirme Özeti</h2>
<div class="summary-section">
  <h3>Genel Bilgiler</h3>
  <p><strong>Sınav Sayısı:</strong> {{ exam_count }}</p>
  <p><strong>Öğrenci Sayısı:</strong> {{ student_count }}</p>
</div>

{% if exams %}
<div class="summary-section">
  <h3>Sınav Detayları</h3>
  <ul>
    {% for exam in exams %}
      <li>
        <strong>{{ exam['name'] }}</strong><br>
        Soru Sayısı: {{ exam['question_count'] }}, Ağırlık: {{ exam['weight'] }}%
      </li>
    {% endfor %}
  </ul>
</div>
{% endif %}

{% if question_points %}
<div class="summary-section">
  <h3>Soru Puanları</h3>
  {% for exam_idx, exam in enumerate(exams) %}
    <h4>{{ exam['name'] }}</h4>
    <p>
    {% for q_idx in range(exam['question_count']|int) %}
      Soru {{ q_idx + 1 }}: {{ question_points[exam_idx][q_idx] }} puan{% if not loop.last %}, {% endif %}
    {% endfor %}
    </p>
  {% endfor %}
</div>
{% endif %}

<a href="{{ url_for('main') }}" class="back-btn">Yeni Değerlendirme Başlat</a>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        exam_count = int(request.form["exam_count"])
        student_count = int(request.form["student_count"])
        session["exam_count"] = exam_count
        session["student_count"] = student_count
        return redirect(url_for("exam_details"))
    return render_template_string(main_page)

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
    
    return render_template_string(exam_details_page, exam_count=exam_count)

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
                points.append(int(request.form.get(key, 0)))
            question_points_list.append(points)
        session["question_points"] = question_points_list
        return redirect(url_for("student_grades"))
    
    return render_template_string(question_points_page, exams=exams)

@app.route("/student_grades", methods=["GET", "POST"])
def student_grades():
    exams = session.get("exams")
    student_count = session.get("student_count")
    question_points = session.get("question_points")
    
    if not exams or not student_count or not question_points:
        return redirect(url_for("main"))
    
    if request.method == "POST":
        students = []
        for student_idx in range(int(student_count)):
            student = {
                "number": request.form[f"student_number_{student_idx}"],
                "name": request.form[f"student_name_{student_idx}"],
                "grades": [],
                "total": request.form[f"total_{student_idx}"]
            }
            
            # Tüm soruların notlarını topla
            total_questions = sum(int(exam["question_count"]) for exam in exams)
            for q_idx in range(total_questions):
                grade = request.form.get(f"grade_{student_idx}_{q_idx}", "0")
                student["grades"].append(float(grade) if grade else 0.0)
            
            students.append(student)
        
        session["students"] = students
        return redirect(url_for("summary"))
    
    return render_template_string(student_grades_page, 
                                exams=exams, 
                                student_count=int(student_count),
                                question_points=question_points,
                                session=session,
                                enumerate=enumerate)

@app.route("/summary")
def summary():
    exam_count = session.get("exam_count")
    student_count = session.get("student_count")
    exams = session.get("exams")
    question_points = session.get("question_points")
    students = session.get("students")
    
    return render_template_string(summary_page, 
                                exam_count=exam_count, 
                                student_count=student_count, 
                                exams=exams, 
                                question_points=question_points,
                                students=students,
                                enumerate=enumerate)

if __name__ == "__main__":
    app.run(port=8080, debug=True)
