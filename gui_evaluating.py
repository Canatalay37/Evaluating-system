from flask import Flask, render_template_string, request, redirect, url_for, session
import numpy as np 

app = Flask(__name__)
app.secret_key = "cok_guclu_bir_gizli_anahtar_buraya_yazilacak_mutlaka_degistirin" 

# HTML TEMPLATELERİ (Yukarıdaki kodunuzdan kopyalanmıştır, burada sadece ilgili kısımlar)
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

clo_details_page = """
<!doctype html>
<html>
<head>
<title>CLO Details</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
form { background: #f5f5f5; padding: 20px; border-radius: 8px; max-width: 600px; }
input[type="text"], input[type="number"] { padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
input[type="submit"] { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
.clo-section { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #ddd; }
</style>
</head>
<body>
<h2>Ders Öğrenim Çıktıları (CLO) Detayları</h2>
<form method="post">
  <label>Kaç adet CLO var? <input type="number" name="clo_count" min="1" max="20" value="{{ clo_count }}" required></label><br><br>
  <div id="clo_names_container">
    {% for i in range(clo_count) %}
      <div class="clo-section">
        <h3>CLO {{ i+1 }}</h3>
        <label>CLO Adı: <input type="text" name="clo_name_{{i}}" placeholder="Örn: CLO{{i+1}}" required></label><br>
      </div>
    {% endfor %}
  </div>
  <input type="submit" value="Kaydet ve Devam Et">
</form>
<script>
    document.querySelector('input[name="clo_count"]').addEventListener('input', function() {
        const count = parseInt(this.value);
        const container = document.getElementById('clo_names_container');
        container.innerHTML = ''; // Clear existing inputs

        if (isNaN(count) || count < 1) return;

        for (let i = 0; i < count; i++) {
            const div = document.createElement('div');
            div.className = 'clo-section';
            div.innerHTML = `
                <h3>CLO ${i+1}</h3>
                <label>CLO Adı: <input type="text" name="clo_name_${i}" placeholder="Örn: CLO${i+1}" required></label><br>
            `;
            container.appendChild(div);
        }
    });
</script>
</body>
</html>
"""

bloom_level_mapping_page = """
<!doctype html>
<html>
<head>
<title>Bloom Level & CLO Mapping</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
h2 { color: #333; }
.container {
    background: #f5f5f5;
    padding: 20px;
    border-radius: 8px;
    max-width: 1200px; 
    margin: 0 auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: center;
    font-size: 10px; 
}
th {
    background-color: #e9ecef;
    font-weight: bold;
}
.clo-row-header {
    background-color: #d1ecf1; 
    font-weight: bold;
    text-align: left;
    min-width: 80px;
}
.exam-header {
    background-color: #cce5ff; 
    font-size: 11px;
    font-weight: bold;
}
.question-header {
    background-color: #f0f0f0;
    font-size: 10px;
    padding: 4px;
}
.input-cell input {
    width: 35px; 
    padding: 2px;
    margin: 1px;
    border: 1px solid #ddd;
    border-radius: 3px;
    text-align: center;
    font-size: 9px;
}
.blue-part-col {
    background-color: #e0f2f7; 
    font-weight: bold;
    color: #0056b3;
}
.total-row {
    background-color: #fffacd; 
    font-weight: bold;
}
.calculated-value {
    background-color: #e6ffe6; 
    color: #006400;
    font-weight: bold;
}
.submit-btn {
    background: #28a745; 
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    margin-top: 20px;
}
.submit-btn:hover {
    background: #218838;
}
</style>
</head>
<body>
<h2>Bloom Seviyesi ve CLO Eşleştirme</h2>
<div class="container">
    <form method="post">
        <table>
            <thead>
                <tr>
                    <th rowspan="2" class="clo-row-header">CLO</th>
                    {% for exam in exams %}
                        <th colspan="{{ exam.question_count * 4 }}" class="exam-header">{{ exam.name }}</th>
                    {% endfor %}
                    <th colspan="2" class="blue-part-col">Mavi Kısım (Hesaplanan)</th> 
                    <th colspan="4" class="blue-part-col">CLO Performans Değerleri</th>
                </tr>
                <tr>
                    {% for exam in exams %}
                        {% for q_idx in range(exam.question_count|int) %}
                            <th colspan="4" class="question-header">Q{{ q_idx + 1 }}</th>
                        {% endfor %}
                    {% endfor %}
                    <th class="blue-part-col">Max CLO Score</th>
                    <th class="blue-part-col">Weighted CLO Score</th>
                    <th class="blue-part-col">Normalized CLO Score</th>
                    <th class="blue-part-col">Max Bloom Score</th>
                    <th class="blue-part-col">Weighted Bloom Score</th>
                    <th class="blue-part-col">Average Bloom Score</th>
                </tr>
                <tr>
                    <th></th> 
                    {% for exam in exams %}
                        {% for q_idx in range(exam.question_count|int) %}
                            <th>QCT(%)</th>
                            <th>W</th>
                            <th>SPM</th> 
                            <th>BL</th>
                        {% endfor %}
                    {% endfor %}
                    <th class="blue-part-col"></th>
                    <th class="blue-part-col"></th>
                    <th class="blue-part-col"></th>
                    <th class="blue-part-col"></th>
                    <th class="blue-part-col"></th>
                    <th class="blue-part-col"></th>
                </tr>
            </thead>
            <tbody>
                {% for clo_idx, clo in enumerate(clos) %}
                <tr>
                    <td class="clo-row-header">{{ clo.name }}</td>
                    {% for exam_idx, exam in enumerate(exams) %}
                        {% for q_idx in range(exam.question_count|int) %}
                            {% set global_q_idx = all_questions_flat_map[exam_idx][q_idx] %}
                            <td class="input-cell">
                                <input type="number" name="qct_{{ clo_idx }}_{{ global_q_idx }}" value="{{ clo_q_data.get(clo_idx, {}).get(global_q_idx, {}).get('qct', '') }}" min="0" max="100" step="1" placeholder="QCT">
                            </td>
                            <td class="input-cell">
                                <input type="number" name="w_{{ clo_idx }}_{{ global_q_idx }}" value="{{ clo_q_data.get(clo_idx, {}).get(global_q_idx, {}).get('w', '') }}" min="0" max="1" step="0.01" placeholder="W">
                            </td>
                            <td class="calculated-value">
                                <span id="spm_{{ clo_idx }}_{{ global_q_idx }}">
                                    {{ '%.2f' % clo_q_data.get(clo_idx, {}).get(global_q_idx, {}).get('spm', 0) if clo_q_data.get(clo_idx, {}).get(global_q_idx, {}).get('spm') is not none else 'N/A' }}
                                </span>
                            </td>
                            <td class="input-cell">
                                <input type="number" name="bl_{{ clo_idx }}_{{ global_q_idx }}" value="{{ clo_q_data.get(clo_idx, {}).get(global_q_idx, {}).get('bl', '') }}" min="1" max="6" step="1" placeholder="BL">
                            </td>
                        {% endfor %}
                    {% endfor %}
                    {# Mavi kısım hesaplanan değerler #}
                    <td class="blue-part-col calculated-value" id="max_clo_score_{{ clo_idx }}">
                        {{ '%.2f' % clo_results.get(clo_idx, {}).get('max_clo_score', 0) }}
                    </td>
                    <td class="blue-part-col calculated-value" id="weighted_clo_score_{{ clo_idx }}">
                        {{ '%.2f' % clo_results.get(clo_idx, {}).get('weighted_clo_score', 0) }}
                    </td>
                    <td class="blue-part-col calculated-value" id="normalized_clo_score_{{ clo_idx }}">
                        {{ '%.2f' % clo_results.get(clo_idx, {}).get('normalized_clo_score', 0) }}
                    </td>
                    <td class="blue-part-col calculated-value" id="max_bloom_score_{{ clo_idx }}">
                        {{ '%.2f' % clo_results.get(clo_idx, {}).get('max_bloom_score', 0) }}
                    </td>
                    <td class="blue-part-col calculated-value" id="weighted_bloom_score_{{ clo_idx }}">
                        {{ '%.2f' % clo_results.get(clo_idx, {}).get('weighted_bloom_score', 0) }}
                    </td>
                    <td class="blue-part-col calculated-value" id="average_bloom_score_{{ clo_idx }}">
                        {{ '%.2f' % clo_results.get(clo_idx, {}).get('average_bloom_score', 0) }}
                    </td>
                </tr>
                {% endfor %}
                <tr class="total-row">
                    <td colspan="{{ 1 + all_questions_flat|length * 4 }}">Toplam</td>
                    <td class="blue-part-col calculated-value" id="total_max_clo_score">
                        {{ '%.2f' % total_clo_results.get('total_max_clo_score', 0) }}
                    </td>
                    <td class="blue-part-col calculated-value" id="total_weighted_clo_score">
                        {{ '%.2f' % total_clo_results.get('total_weighted_clo_score', 0) }}
                    </td>
                     <td class="blue-part-col calculated-value" id="total_normalized_clo_score">
                        {{ '%.2f' % total_clo_results.get('total_normalized_clo_score', 0) }}
                    </td>
                     <td class="blue-part-col calculated-value" id="total_max_bloom_score">
                        {{ '%.2f' % total_clo_results.get('total_max_bloom_score', 0) }}
                    </td>
                     <td class="blue-part-col calculated-value" id="total_weighted_bloom_score">
                        {{ '%.2f' % total_clo_results.get('total_weighted_bloom_score', 0) }}
                    </td>
                     <td class="blue-part-col calculated-value" id="total_average_bloom_score">
                        {{ '%.2f' % total_clo_results.get('total_average_bloom_score', 0) }}
                    </td>
                </tr>
            </tbody>
        </table>
        <button type="submit" class="submit-btn">Değerleri Kaydet ve Hesapla</button>
    </form>
</div>

<script>
    const exams = {{ exams | tojson }};
    const clos = {{ clos | tojson }};
    const allQuestionsFlat = {{ all_questions_flat | tojson }};
    const studentsData = {{ students_data | tojson }}; 
    const studentCount = {{ student_count }}; 

    function calculateSPM(globalQuestionIdx, allStudentsData) {
        const gradesForQuestion = [];
        allStudentsData.forEach(student => {
            // Check if student and student.grades exist, and if globalQuestionIdx is a valid index
            if (student && student.grades && globalQuestionIdx < student.grades.length) {
                const grade = student.grades[globalQuestionIdx];
                if (grade !== null && grade !== undefined) { // Check for null or undefined grades
                    gradesForQuestion.push(grade);
                }
            }
        });

        if (gradesForQuestion.length === 0) {
            return 0; 
        }

        gradesForQuestion.sort((a, b) => a - b);
        const mid = Math.floor(gradesForQuestion.length / 2);
        const median = gradesForQuestion.length % 2 === 0
            ? (gradesForQuestion[mid - 1] + gradesForQuestion[mid]) / 2
            : gradesForQuestion[mid];
        
        const questionMaxPoints = allQuestionsFlat.find(q => q.global_question_idx === globalQuestionIdx)?.max_points || 0;

        if (questionMaxPoints === 0) {
            return 0;
        }

        return (median / questionMaxPoints) * 100;
    }

    document.addEventListener('DOMContentLoaded', function() {
        const inputs = document.querySelectorAll('input[type="number"][name^="qct_"], input[type="number"][name^="w_"], input[type="number"][name^="bl_"]');

        inputs.forEach(input => {
            input.addEventListener('input', updateCalculations);
            input.addEventListener('change', updateCalculations);
        });

        allQuestionsFlat.forEach(q => {
            const spmValue = calculateSPM(q.global_question_idx, studentsData);
            document.querySelectorAll(`span[id^="spm_"][id$="_${q.global_question_idx}"]`).forEach(spmSpan => {
                spmSpan.textContent = spmValue.toFixed(2);
            });
        });

        // Initial calculation on page load
        updateCalculations(); 
    });

    function updateCalculations() {
        const cloResults = {};
        const totalCloResults = {
            total_max_clo_score: 0,
            total_weighted_clo_score: 0,
            total_normalized_clo_score: 0,
            total_max_bloom_score: 0,
            total_weighted_bloom_score: 0,
            total_average_bloom_score: 0
        };

        clos.forEach((clo, cloIdx) => {
            let maxCloScore = 0;
            let weightedCloScore = 0;
            let maxBloomScore = 0; 
            let weightedBloomScore = 0;

            allQuestionsFlat.forEach(q => {
                const globalQIdx = q.global_question_idx;
                const qctInput = document.querySelector(`input[name="qct_${cloIdx}_${globalQIdx}"]`);
                const wInput = document.querySelector(`input[name="w_${cloIdx}_${globalQIdx}"]`);
                const blInput = document.querySelector(`input[name="bl_${cloIdx}_${globalQIdx}"]`);
                const spmSpan = document.getElementById(`spm_${cloIdx}_${globalQIdx}`);

                // Parse values to float, defaulting to 0 if not a valid number
                const qct = parseFloat(qctInput?.value) || 0;
                const w = parseFloat(wInput?.value) || 0;
                const bl = parseFloat(blInput?.value) || 0;
                const spm = parseFloat(spmSpan?.textContent) || 0; 

                maxCloScore += (qct / 100) * w;
                weightedCloScore += (qct / 100) * w * spm;
                maxBloomScore += (qct / 100) * w * bl;
                weightedBloomScore += (qct / 100) * w * bl;
            });

            const normalizedCloScore = (maxCloScore > 0) ? (weightedCloScore / maxCloScore) : 0;
            const averageBloomScore = (maxCloScore > 0) ? (weightedBloomScore / maxCloScore) : 0;

            cloResults[cloIdx] = {
                max_clo_score: maxCloScore,
                weighted_clo_score: weightedCloScore,
                normalized_clo_score: normalizedCloScore,
                max_bloom_score: maxBloomScore, 
                weighted_bloom_score: weightedBloomScore, 
                average_bloom_score: averageBloomScore
            };

            document.getElementById(`max_clo_score_${cloIdx}`).textContent = maxCloScore.toFixed(2);
            document.getElementById(`weighted_clo_score_${clo_idx}`).textContent = weightedCloScore.toFixed(2);
            document.getElementById(`normalized_clo_score_${clo_idx}`).textContent = normalizedCloScore.toFixed(2);
            document.getElementById(`max_bloom_score_${clo_idx}`).textContent = maxBloomScore.toFixed(2); 
            document.getElementById(`weighted_bloom_score_${clo_idx}`).textContent = weightedBloomScore.toFixed(2); 
            document.getElementById(`average_bloom_score_${clo_idx}`).textContent = averageBloomScore.toFixed(2);

            totalCloResults.total_max_clo_score += maxCloScore;
            totalCloResults.total_weighted_clo_score += weightedCloScore;
            // Normalized and average bloom scores for total row are not simply sums,
            // they require re-calculation based on total weighted and max scores.
            // For now, these are kept as sums of individual CLO scores for display purposes,
            // but might need re-evaluation based on specific calculation requirements.
            totalCloResults.total_normalized_clo_score += normalizedCloScore; 
            totalCloResults.total_max_bloom_score += maxBloomScore;
            totalCloResults.total_weighted_bloom_score += weightedBloomScore;
            totalCloResults.total_average_bloom_score += averageBloomScore; 

        });

        document.getElementById('total_max_clo_score').textContent = totalCloResults.total_max_clo_score.toFixed(2);
        document.getElementById('total_weighted_clo_score').textContent = totalCloResults.total_weighted_clo_score.toFixed(2);
        // These totals are conceptually problematic as sums of normalized/average values.
        // They are marked 'N/A' as sums. If actual overall normalized/average is needed,
        // it must be calculated differently (e.g., total_weighted_clo_score / total_max_clo_score).
        document.getElementById('total_normalized_clo_score').textContent = "N/A"; 
        document.getElementById('total_max_bloom_score').textContent = totalCloResults.total_max_bloom_score.toFixed(2);
        document.getElementById('total_weighted_bloom_score').textContent = totalCloResults.total_weighted_bloom_score.toFixed(2);
        document.getElementById('total_average_bloom_score').textContent = "N/A"; 

    }
</script>
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
  border-bottom: 1px solid #fff; 
}
.tab-content {
  display: none; 
  padding: 20px 0;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 8px 8px;
  background: #f9f9f9;
}
.tab-content.active {
  display: block; 
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

.top-right-button {
    position: absolute;
    top: 20px;
    right: 20px;
    background-color: #6f42c1; 
    color: white;
    padding: 10px 15px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 14px;
    text-decoration: none; 
}
.top-right-button:hover {
    background-color: #5936a0;
}

</style>
</head>
<body>
<h2>Öğrenci Bilgileri ve Not Girişi</h2>

<a href="{{ url_for('bloom_level_mapping') }}" class="top-right-button">Bloom Level System</a>

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
              {% if q_flat.exam_idx == exam_idx %} 
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
              <td><input type="text" name="student_number_{{ student_idx }}" placeholder="Öğr. No" style="width:95%;" value="{{ students_data[student_idx].number if students_data[student_idx] else '' }}"></td>
              <td><input type="text" name="student_name_{{ student_idx }}" placeholder="Ad Soyad" style="width:95%;" value="{{ students_data[student_idx].name if students_data[student_idx] else '' }}"></td>
              {% for q_flat in all_questions_flat %}
                {% if q_flat.exam_idx == exam_idx %} 
                <td>
                  <input type="number" 
                         class="grade-input" 
                         name="grade_{{ student_idx }}_{{ q_flat.global_question_idx }}" 
                         min="0" 
                         max="{{ q_flat.max_points }}" 
                         step="0.5"
                         data-student="{{ student_idx }}" 
                         data-question="{{ q_flat.global_question_idx }}"
                         value="{{ students_data[student_idx].grades[q_flat.global_question_idx] if students_data[student_idx] and students_data[student_idx].grades|length > q_flat.global_question_idx else '' }}"
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
            <td>{{ current_exam_total_possible_points }}</td> 
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
        allQuestionsFlat.filter(q => q.exam_idx === examIdx).forEach(q => {
            let inp = document.querySelector(`input[name='grade_${studentIdx}_${q.global_question_idx}']`);
            if (inp && inp.value !== "" && !isNaN(parseFloat(inp.value))) {
                total += parseFloat(inp.value);
            }
        });
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
  
  let sortedVals = [...vals].sort((a,b) => a - b);
  let medianValue = sortedVals.length % 2 === 1 
    ? sortedVals[Math.floor(sortedVals.length / 2)]
    : (sortedVals[sortedVals.length / 2 - 1] + sortedVals[sortedVals.length / 2]) / 2;
  
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
    if (!activeTabContent) return; 

    const activeTabId = activeTabContent.id;
    const activeExamIdx = parseInt(activeTabId.replace('exam-', ''));
    
    const currentExamQuestions = allQuestionsFlat.filter(q => q.exam_idx === activeExamIdx);

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
    
    for (let q = 0; q < currentExamQuestions.length; q++) {
        let globalQIdx = currentExamQuestions[q].global_question_idx;
        let vals = getColumnValues(globalQIdx);
        let stats = calcStats(vals);
        
        let maxInput = activeTabContent.querySelector(`.max-q[data-question='${globalQIdx}']`);
        let minInput = activeTabContent.querySelector(`.min-q[data-question='${globalQIdx}']`);
        let avgInput = activeTabContent.querySelector(`.avg-q[data-question='${globalQIdx}']`);
        let medianInput = activeTabContent.querySelector(`.median-q[data-question='${globalQIdx}']`);
        
        if (maxInput) maxInput.value = stats.max !== '' ? stats.max.toFixed(1) : '';
        if (minInput) minInput.value = stats.min !== '' ? stats.min.toFixed(1) : '';
        if (avgInput) avgInput.value = stats.avg !== '' ? stats.avg.toFixed(1) : '';
        if (medianInput) medianInput.value = stats.median !== '' ? stats.median.toFixed(1) : '';
        
        let perfMedian = calculatePerformanceMedianForQuestion(globalQIdx, currentExamQuestions[q].max_points);
        let perfInput = activeTabContent.querySelector(`.performance-median[data-question='${globalQIdx}']`);
        if (perfInput) perfInput.value = perfMedian !== '' ? perfMedian.toFixed(2) : '';
    }
    
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

    let examPerfMedian = calculateExamPerformanceMedian(activeExamIdx);
    let perfExamTotalInput = activeTabContent.querySelector(`.performance-median-exam-total[data-exam='${activeExamIdx}']`);
    if (perfExamTotalInput) perfExamTotalInput.value = examPerfMedian !== '' ? examPerfMedian.toFixed(2) : '';
}

function openTab(event, tabId) {
  document.querySelectorAll('.tab-content').forEach(tabContent => {
    tabContent.classList.remove('active');
  });

  document.querySelectorAll('.tab-button').forEach(tabButton => {
    tabButton.classList.remove('active');
  });

  document.getElementById(tabId).classList.add('active');

  event.currentTarget.classList.add('active');

  recalcCurrentTabStats();
}

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', (event) => {
      openTab(event, button.dataset.tab);
    });
  });

  document.querySelectorAll('.grade-input').forEach(function(inp) {
    inp.addEventListener('input', recalcCurrentTabStats);
    inp.addEventListener('change', recalcCurrentTabStats);
  });
  
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
                points.append(float(request.form.get(key, 0))) 
            question_points_list.append(points)
        session["question_points"] = question_points_list
        return redirect(url_for("clo_details"))
    
    return render_template_string(question_points_page, exams=exams, enumerate=enumerate)

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

    return render_template_string(clo_details_page, clo_count=clo_count, enumerate=enumerate)

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

    return render_template_string(
        bloom_level_mapping_page,
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
    
    return render_template_string(student_grades_page, 
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
    
    return render_template_string(summary_page, 
                                exam_count=exam_count, 
                                student_count=student_count, 
                                exams=exams, 
                                question_points=question_points,
                                students=students,
                                clos=clos,
                                enumerate=enumerate) 

if __name__ == "__main__":
    app.run(port=8080, debug=True)
