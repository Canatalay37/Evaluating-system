from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
# Burayı daha güvenli bir anahtar ile değiştirmeyi unutmayın!
app.secret_key = "cok_guclu_bir_gizli_anahtar_buraya_yazilacak_mutlaka_degistirin" 

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
  {% for exam_idx, exam in enumerate(exams) %}
    <div class="exam-section">
      <h3>{{ exam['name'] }}</h3>
      <div class="question-grid">
        {% for q in range(exam['question_count']|int) %}
          <label>Soru {{ q+1 }}: <input type="number" name="points_{{exam_idx}}_{{q}}" min="0" max="100" required></label>
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
.tabs {
  display: flex;
  margin-bottom: 15px;
  border-bottom: 1px solid #ddd;
}
.tab-button {
  background-color: #f0f0f0;
  border: 1px solid #ddd;
  border-bottom: none;
  padding: 10px 15px;
  cursor: pointer;
  border-top-left-radius: 5px;
  border-top-right-radius: 5px;
  margin-right: 5px;
  font-weight: bold;
}
.tab-button.active {
  background-color: #fff;
  border-color: #007bff;
  color: #007bff;
  border-bottom: 1px solid #fff; /* Active tab visually overlaps the border */
}
.tab-content {
  display: none; /* Hide all tab contents by default */
  padding: 20px 0;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 8px 8px;
  background: #f9f9f9;
}
.tab-content.active {
  display: block; /* Show active tab content */
}

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

<form method='post'>
  <div class="tabs">
    {% for exam_idx, exam in enumerate(exams) %}
      <button type="button" class="tab-button {% if loop.first %}active{% endif %}" data-tab="exam-{{ exam_idx }}">
        {{ exam.name }}
      </button>
    {% endfor %}
  </div>

  {% for exam_idx, exam in enumerate(exams) %}
    <div id="exam-{{ exam_idx }}" class="tab-content {% if loop.first %}active{% endif %}">
      <h3>{{ exam.name }} Sınavı Not Girişi</h3>
      <table>
        <thead>
          <tr>
            <th class="id-col">ID</th>
            <th class="student-info-col">Öğrenci No</th>
            <th class="student-info-col">Ad-Soyad</th>
            {% for q_flat in all_questions_flat %}
              {% if q_flat.exam_idx == exam_idx %} {# Sadece bu sınava ait soruları göster #}
                <th class="question-col">Soru {{ q_flat.question_idx_in_exam + 1 }}</th>
              {% endif %}
            {% endfor %}
            <th class="total-col">Toplam</th>
          </tr>
        </thead>
        <tbody>
          {% for student_idx in range(student_count) %}
            <tr class="student-row">
              <td>{{ student_idx + 1 }}</td>
              <td><input type="text" name="student_number_{{ student_idx }}" placeholder="Öğr. No" style="width:95%;" value="{{ students_data.get(student_idx, {}).get('number', '') }}"></td>
              <td><input type="text" name="student_name_{{ student_idx }}" placeholder="Ad Soyad" style="width:95%;" value="{{ students_data.get(student_idx, {}).get('name', '') }}"></td>
              {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %} {# Sadece bu sınava ait soruları göster #}
                <td>
                  <input type="number" 
                         class="grade-input" 
                         name="grade_{{ student_idx }}_{{ q_flat.global_question_idx }}" 
                         min="0" 
                         max="{{ q_flat.max_points }}" 
                         step="0.5"
                         data-student="{{ student_idx }}" 
                         data-question="{{ q_flat.global_question_idx }}"
                         value="{{ students_data.get(student_idx, {}).get('grades', [])[q_flat.global_question_idx] if students_data.get(student_idx, {}).get('grades', [])|length > q_flat.global_question_idx else '' }}"
                         style="width:40px;">
                </td>
                {% endif %}
              {% endfor %}
              <td><input type="text" class="exam-total-input" data-student="{{ student_idx }}" data-exam="{{ exam_idx }}" readonly style="width:50px;" value=""></td>
            </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr class="stats-row">
            <th>Max</th>
            <td colspan="2"></td>
            {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %}
                    <td><input type="text" class="max-q" data-question="{{ q_flat.global_question_idx }}" readonly style="width:40px;"></td>
                {% endif %}
            {% endfor %}
            <td><input type="text" class="max-exam-total" data-exam="{{ exam_idx }}" readonly style="width:50px;"></td>
          </tr>
          
          <tr class="stats-row">
            <th>Min</th>
            <td colspan="2"></td>
            {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %}
                    <td><input type="text" class="min-q" data-question="{{ q_flat.global_question_idx }}" readonly style="width:40px;"></td>
                {% endif %}
            {% endfor %}
            <td><input type="text" class="min-exam-total" data-exam="{{ exam_idx }}" readonly style="width:50px;"></td>
          </tr>
          
          <tr class="stats-row">
            <th>Ortalama</th>
            <td colspan="2"></td>
            {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %}
                    <td><input type="text" class="avg-q" data-question="{{ q_flat.global_question_idx }}" readonly style="width:40px;"></td>
                {% endif %}
            {% endfor %}
            <td><input type="text" class="avg-exam-total" data-exam="{{ exam_idx }}" readonly style="width:50px;"></td>
          </tr>
          
          <tr class="stats-row">
            <th>Medyan</th>
            <td colspan="2"></td>
            {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %}
                    <td><input type="text" class="median-q" data-question="{{ q_flat.global_question_idx }}" readonly style="width:40px;"></td>
                {% endif %}
            {% endfor %}
            <td><input type="text" class="median-exam-total" data-exam="{{ exam_idx }}" readonly style="width:50px;"></td>
          </tr>
          
          <tr class="total-points-row">
            <th>Toplam</th>
            <td colspan="2"></td>
            {% set current_exam_total_possible_points = 0 %}
            {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %}
                    <td>{{ q_flat.max_points }}</td>
                    {% set current_exam_total_possible_points = current_exam_total_possible_points + q_flat.max_points %}
                {% endif %}
            {% endfor %}
            <td>{{ current_exam_total_possible_points }}</td> {# Bu sınavın toplam puanı #}
          </tr>
          
          <tr class="performance-row">
            <th colspan="3">Öğrenci Performans Medyanı (%)</th>
            {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %}
                    <td><input type="text" class="performance-median" data-question="{{ q_flat.global_question_idx }}" readonly style="width:40px;"></td>
                {% endif %}
            {% endfor %}
            <td><input type="text" class="performance-median-exam-total" data-exam="{{ exam_idx }}" readonly style="width:50px;"></td>
          </tr>
        </tfoot>
      </table>
    </div>
  {% endfor %}

  <br>
  <input type="submit" value="Kaydet ve Özet Görüntüle" class="submit-btn">
</form>

<script>
const exams = {{ exams | tojson }};
const studentCount = {{ student_count }};
// all_questions_flat objesi Python tarafından zaten sağlanıyor, direkt kullanacağız.
const allQuestionsFlat = {{ all_questions_flat | tojson }}; 


function getColumnValues(globalColIdx) {
  let vals = [];
  for (let i = 0; i < studentCount; i++) {
    let inp = document.querySelector(`input[name='grade_${i}_${globalColIdx}']`);
    if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
      vals.push(parseFloat(inp.value));
    }
  }
  return vals;
}

function getExamTotalValues(examIdx) {
    let vals = [];
    for (let studentIdx = 0; studentIdx < studentCount; studentIdx++) {
        let total = 0;
        // Sadece ilgili sınava ait soruları topla
        allQuestionsFlat.filter(q => q.exam_idx === examIdx).forEach(q => {
            let inp = document.querySelector(`input[name='grade_${studentIdx}_${q.global_question_idx}']`);
            if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
                total += parseFloat(inp.value);
            }
        });
        // Sadece geçerli, sayısal total değerlerini ekle
        if (!isNaN(total)) {
            vals.push(total);
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
    min: Math.min(...arr),
    avg: parseFloat(avg.toFixed(1)),
    median: parseFloat(median.toFixed(1))
  };
}

function calculatePerformanceMedianForQuestion(globalQuestionIdx, questionMaxPoints) {
  let vals = getColumnValues(globalQuestionIdx);
  if (vals.length === 0 || questionMaxPoints === 0) return '';
  
  // Soru medyanını hesapla
  let sortedVals = [...vals].sort((a,b) => a - b);
  let medianValue = sortedVals.length % 2 === 1 
    ? sortedVals[Math.floor(sortedVals.length / 2)]
    : (sortedVals[sortedVals.length / 2 - 1] + sortedVals[sortedVals.length / 2]) / 2;
  
  // Performans Medyanı = (Soru Medyanı / Soru Maksimum Puanı) * 100
  let performanceMedian = (medianValue / questionMaxPoints) * 100;
  
  return parseFloat(performanceMedian.toFixed(2));
}

function calculateExamPerformanceMedian(examIdx) {
    let studentExamTotals = getExamTotalValues(examIdx);
    if (studentExamTotals.length === 0) return '';

    const currentExamTotalPossiblePoints = allQuestionsFlat
        .filter(q => q.exam_idx === examIdx)
        .reduce((sum, q) => sum + q.max_points, 0);

    if (currentExamTotalPossiblePoints === 0) return '';

    let sortedStudentExamTotals = [...studentExamTotals].sort((a,b) => a - b);
    let medianExamTotalValue = sortedStudentExamTotals.length % 2 === 1 
      ? sortedStudentExamTotals[Math.floor(sortedStudentExamTotals.length / 2)]
      : (sortedStudentExamTotals[sortedStudentExamTotals.length / 2 - 1] + sortedStudentExamTotals[sortedStudentExamTotals.length / 2]) / 2;
        
    let performanceMedian = (medianExamTotalValue / currentExamTotalPossiblePoints) * 100;
    return parseFloat(performanceMedian.toFixed(2));
}


function recalcCurrentTabStats() {
    const activeTabContent = document.querySelector('.tab-content.active');
    if (!activeTabContent) return; // No active tab, do nothing

    const activeTabId = activeTabContent.id;
    const activeExamIdx = parseInt(activeTabId.replace('exam-', ''));
    
    const currentExamQuestions = allQuestionsFlat.filter(q => q.exam_idx === activeExamIdx);

    // Her öğrenci için ilgili sınavın toplamını hesapla
    for (let i = 0; i < studentCount; i++) {
        let total = 0;
        currentExamQuestions.forEach(q => {
            let inp = document.querySelector(`input[name='grade_${i}_${q.global_question_idx}']`);
            if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
                total += parseFloat(inp.value);
            }
        });
        let totalInput = document.querySelector(`.exam-total-input[data-student='${i}'][data-exam='${activeExamIdx}']`);
        if (totalInput) {
            totalInput.value = total.toFixed(1); 
        }
    }
    
    // Her soru için istatistikler (sadece aktif sınavın soruları için)
    currentExamQuestions.forEach(q => {
        let vals = getColumnValues(q.global_question_idx);
        let stats = calcStats(vals);
        
        // Max, Min, Avg, Median
        let maxInput = activeTabContent.querySelector(`.max-q[data-question='${q.global_question_idx}']`);
        let minInput = activeTabContent.querySelector(`.min-q[data-question='${q.global_question_idx}']`);
        let avgInput = activeTabContent.querySelector(`.avg-q[data-question='${q.global_question_idx}']`);
        let medianInput = activeTabContent.querySelector(`.median-q[data-question='${q.global_question_idx}']`);
        
        if (maxInput) maxInput.value = stats.max !== '' ? stats.max.toFixed(1) : '';
        if (minInput) minInput.value = stats.min !== '' ? stats.min.toFixed(1) : '';
        if (avgInput) avgInput.value = stats.avg !== '' ? stats.avg.toFixed(1) : '';
        if (medianInput) medianInput.value = stats.median !== '' ? stats.median.toFixed(1) : '';
        
        // Performans medyanı
        let perfMedian = calculatePerformanceMedianForQuestion(q.global_question_idx, q.max_points);
        let perfInput = activeTabContent.querySelector(`.performance-median[data-question='${q.global_question_idx}']`);
        if (perfInput) perfInput.value = perfMedian !== '' ? perfMedian.toFixed(2) : '';
    });
    
    // Toplam sütun istatistikleri (sadece aktif sınavın toplamları için)
    let examTotalVals = getExamTotalValues(activeExamIdx);
    let tStats = calcStats(examTotalVals);
    
    let maxTotalInput = activeTabContent.querySelector(`.max-exam-total[data-exam='${activeExamIdx}']`);
    let minTotalInput = activeTabContent.querySelector(`.min-exam-total[data-exam='${activeExamIdx}']`);
    let avgTotalInput = activeTabContent.querySelector(`.avg-exam-total[data-exam='${activeExamIdx}']`);
    let medianTotalInput = activeTabContent.querySelector(`.median-exam-total[data-exam='${activeExamIdx}']`);
    
    if (maxTotalInput) maxTotalInput.value = tStats.max !== '' ? tStats.max.toFixed(1) : '';
    if (minTotalInput) minTotalInput.value = tStats.min !== '' ? tStats.min.toFixed(1) : '';
    if (avgTotalInput) avgTotalInput.value = tStats.avg !== '' ? tStats.avg.toFixed(1) : '';
    if (medianTotalInput) medianTotalInput.value = tStats.median !== '' ? tStats.median.toFixed(1) : '';

    // Sınav performans medyanı
    let examPerfMedian = calculateExamPerformanceMedian(activeExamIdx);
    let perfExamTotalInput = activeTabContent.querySelector(`.performance-median-exam-total[data-exam='${activeExamIdx}']`);
    if (perfExamTotalInput) perfExamTotalInput.value = examPerfMedian !== '' ? examPerfMedian.toFixed(2) : '';
}


// Tab geçişi fonksiyonu
function openTab(event, tabId) {
  // Tüm tab içeriklerini gizle
  document.querySelectorAll('.tab-content').forEach(tabContent => {
    tabContent.classList.remove('active');
  });

  // Tüm tab butonlarını deaktive et
  document.querySelectorAll('.tab-button').forEach(tabButton => {
    tabButton.classList.remove('active');
  });

  // Tıklanan tab içeriğini göster
  document.getElementById(tabId).classList.add('active');

  // Tıklanan tab butonunu aktif yap
  event.currentTarget.classList.add('active');

  // Yeni aktif olan sekmenin istatistiklerini yeniden hesapla
  recalcCurrentTabStats();
}


// Event listener'ları ekle
document.addEventListener('DOMContentLoaded', function() {
  // Tab butonlarına click listener ekle
  document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', (event) => {
      openTab(event, button.dataset.tab);
    });
  });

  // Tüm not girişlerini dinle
  document.querySelectorAll('.grade-input').forEach(function(inp) {
    inp.addEventListener('input', recalcCurrentTabStats);
    inp.addEventListener('change', recalcCurrentTabStats);
  });
  
  // Sayfa yüklendiğinde ve ilk tab aktifken hesapla
  // Bir zamanlayıcı ile tetikleme, DOM'un tam olarak hazır olmasını sağlayabilir
  setTimeout(recalcCurrentTabStats, 100); 
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
table { border-collapse: collapse; width: 100%; margin-top: 15px; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background-color: #e9ecef; }
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

{% if students %}
<div class="summary-section">
  <h3>Öğrenci Notları ve Genel Puanları</h3>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Öğrenci No</th>
        <th>Ad-Soyad</th>
        <th>Toplam Puan</th>
      </tr>
    </thead>
    <tbody>
      {% for student in students %}
        <tr>
          <td>{{ loop.index }}</td>
          <td>{{ student.number }}</td>
          <td>{{ student.name }}</td>
          <td>{{ student.total }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
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
        session.pop("exams", None) # Yeni bir akış başlatırken eski verileri temizle
        session.pop("question_points", None)
        session.pop("students", None)
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
    
    # enumerate'i Jinja2'ye aktarıyoruz
    return render_template_string(exam_details_page, exam_count=exam_count, enumerate=enumerate) 

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
                points.append(float(request.form.get(key, 0))) # Puanları float olarak al
            question_points_list.append(points)
        session["question_points"] = question_points_list
        return redirect(url_for("student_grades"))
    
    # enumerate'i Jinja2'ye aktarıyoruz
    return render_template_string(question_points_page, exams=exams, enumerate=enumerate)

@app.route("/student_grades", methods=["GET", "POST"])
def student_grades():
    exams = session.get("exams")
    student_count = session.get("student_count")
    question_points_nested = session.get("question_points")
    
    if not exams or not student_count or not question_points_nested:
        return redirect(url_for("main"))
    
    # Tüm soruları düzleştirilmiş bir liste olarak hazırlayalım (Python tarafında)
    # Bu liste, HTML ve JavaScript'teki global_question_idx ile eşleşecek
    all_questions_flat_for_jinja = []
    global_q_idx_counter = 0
    for exam_idx, exam in enumerate(exams):
        for q_idx_in_exam in range(exam['question_count']):
            # question_points_nested'in varlığını ve ilgili indeksin erişilebilirliğini kontrol edin
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

    # Mevcut öğrenci verilerini session'dan al (GET isteği veya önceki POST hatasında)
    students_data = session.get('students', {}) 
    # students_data'yı bir liste yerine, student_idx'i anahtar olarak kullanan bir dict'e dönüştürelim
    students_data_dict = {}
    if isinstance(students_data, list): 
        for idx, student in enumerate(students_data):
            students_data_dict[idx] = student
    else: 
        students_data_dict = students_data

    if request.method == "POST":
        students = []
        total_questions_count = len(all_questions_flat_for_jinja)

        for student_idx in range(int(student_count)):
            student_grades_list = [0.0] * total_questions_count 
            student_total_score = 0.0

            student_number = request.form.get(f"student_number_{student_idx}", "")
            student_name = request.form.get(f"student_name_{student_idx}", "")

            for q_flat in all_questions_flat_for_jinja:
                grade_key = f"grade_{student_idx}_{q_flat['global_question_idx']}"
                grade = request.form.get(grade_key, "0.0")
                try:
                    grade_value = float(grade)
                except ValueError:
                    grade_value = 0.0 
                
                student_grades_list[q_flat['global_question_idx']] = grade_value
                
                student_total_score += grade_value


            students.append({
                "number": student_number,
                "name": student_name,
                "grades": student_grades_list, 
                "total": round(student_total_score, 1) 
            })
        
        session["students"] = students
        return redirect(url_for("summary"))
    
    # GET isteği veya ilk yükleme
    return render_template_string(student_grades_page, 
                                exams=exams, 
                                student_count=int(student_count),
                                question_points_nested=question_points_nested, 
                                students_data=students_data_dict, 
                                all_questions_flat=all_questions_flat_for_jinja, 
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
    