def login():
    password = "insaat2025"  # Hocanın belirlediği şifre
    giris = input("Şifreyi giriniz: ")
    if giris == password:
        print("Giriş başarılı!\n")
    else:
        print("Hatalı şifre! Program sonlandırılıyor.")
        exit()

def exam_details():
    print("Sınav detaylarını giriniz:")
    exam = {}
    exam["Sınav Adı"] = input("Sınav adı: ")
    exam["Soru Sayısı"] = input("Toplam soru sayısı: ")
    exam["Sınav Tarihi"] = input("Sınav tarihi: ")
    print("\nSınav detayları kaydedildi.\n")
    return exam

login()
exam_info = exam_details()

students = {}

def add_student():
    name = input("Öğrenci adı: ")
    if name in students:
        print("Bu isimde bir öğrenci zaten var.")
    else:
        students[name] = {"vize": [], "final": [], "quiz": []}
        print(f"{name} eklendi.")

def add_vize_grades():
    name = input("Vize notu eklemek istediğiniz öğrenci adı: ")
    if name in students:
        try:
            soru_sayisi = int(exam_info["Soru Sayısı"])
            grades = []
            for i in range(1, soru_sayisi + 1):
                while True:
                    try:
                        grade = float(input(f"Vize {i}. Soru notu: "))
                        grades.append(grade)
                        break
                    except ValueError:
                        print("Lütfen geçerli bir sayı girin.")
            students[name]["vize"] = grades
            print(f"{name} öğrencisinin vize soru başı notları kaydedildi.")
        except ValueError:
            print("Soru sayısı hatalı.")
    else:
        print("Öğrenci bulunamadı.")

def add_final_grades():
    name = input("Final notu eklemek istediğiniz öğrenci adı: ")
    if name in students:
        try:
            soru_sayisi = int(exam_info["Soru Sayısı"])
            grades = []
            for i in range(1, soru_sayisi + 1):
                while True:
                    try:
                        grade = float(input(f"Final {i}. Soru notu: "))
                        grades.append(grade)
                        break
                    except ValueError:
                        print("Lütfen geçerli bir sayı girin.")
            students[name]["final"] = grades
            print(f"{name} öğrencisinin final soru başı notları kaydedildi.")
        except ValueError:
            print("Soru sayısı hatalı.")
    else:
        print("Öğrenci bulunamadı.")

def add_quiz_grades():
    name = input("Quiz notu eklemek istediğiniz öğrenci adı: ")
    if name in students:
        try:
            soru_sayisi = int(exam_info["Soru Sayısı"])
            grades = []
            for i in range(1, soru_sayisi + 1):
                while True:
                    try:
                        grade = float(input(f"Quiz {i}. Soru notu: "))
                        grades.append(grade)
                        break
                    except ValueError:
                        print("Lütfen geçerli bir sayı girin.")
            students[name]["quiz"] = grades
            print(f"{name} öğrencisinin quiz soru başı notları kaydedildi.")
        except ValueError:
            print("Soru sayısı hatalı.")
    else:
        print("Öğrenci bulunamadı.")

def list_students():
    if not students:
        print("Henüz öğrenci eklenmedi.")
    else:
        for name, exams in students.items():
            print(f"{name}:")
            for exam_type, grades in exams.items():
                print(f"  {exam_type.capitalize()}: {grades}")

def main_menu():
    while True:
        print("\n1. Öğrenci ekle\n2. Vize notu ekle\n3. Final notu ekle\n4. Quiz notu ekle\n5. Öğrencileri listele\n6. Çıkış")
        choice = input("Seçiminiz: ")
        if choice == "1":
            add_student()
        elif choice == "2":
            add_vize_grades()
        elif choice == "3":
            add_final_grades()
        elif choice == "4":
            add_quiz_grades()
        elif choice == "5":
            list_students()
        elif choice == "6":
            print("Programdan çıkılıyor.")
            break
        else:
            print("Geçersiz seçim, tekrar deneyin.")

main_menu()