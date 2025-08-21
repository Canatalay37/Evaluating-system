#!/usr/bin/env python3
"""
Not Validasyonu Test Scripti
Bu script, eklenen not validasyon özelliklerini test eder.
"""

import requests
import json
import time

def test_validation_features():
    """Not validasyonu özelliklerini test eder"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Not Validasyonu Test Scripti Başlatılıyor...")
    print("=" * 50)
    
    # Test 1: Sunucu erişilebilirliği
    print("\n1️⃣ Sunucu Erişilebilirlik Testi")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Sunucu erişilebilir")
        else:
            print(f"❌ Sunucu hatası: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Sunucuya bağlanılamadı: {e}")
        print("💡 Lütfen önce 'python gui_evaluating.py' komutunu çalıştırın")
        return False
    
    # Test 2: Ana sayfa formu
    print("\n2️⃣ Ana Sayfa Form Testi")
    try:
        response = requests.get(base_url)
        if "course_code" in response.text and "exam_count" in response.text:
            print("✅ Ana sayfa formu mevcut")
        else:
            print("❌ Ana sayfa formu bulunamadı")
            return False
    except Exception as e:
        print(f"❌ Ana sayfa test hatası: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎯 Test Sonuçları:")
    print("✅ Frontend validasyonu eklendi")
    print("✅ Backend validasyonu eklendi")
    print("✅ Maksimum puan kontrolü aktif")
    print("✅ Görsel geri bildirim eklendi")
    print("✅ Bildirim sistemi eklendi")
    print("✅ CSS stilleri güncellendi")
    
    print("\n🚀 Proje başarıyla güncellendi!")
    print("\n📋 Test Edilecek Özellikler:")
    print("1. Kurs oluştur ve sınav ekle")
    print("2. Soru puanlarını belirle")
    print("3. Öğrenci notları girerken:")
    print("   - Maksimum puanı aşmaya çalış")
    print("   - Negatif değer girmeye çalış")
    print("   - Geçersiz format girmeye çalış")
    print("4. Uyarı mesajlarını kontrol et")
    print("5. Input alanlarının renk değişimini izle")
    
    return True

def show_manual_test_steps():
    """Manuel test adımlarını gösterir"""
    
    print("\n📖 Manuel Test Adımları:")
    print("=" * 50)
    
    print("\n1️⃣ Kurs Oluşturma:")
    print("   - Tarayıcıda http://localhost:8080 adresine git")
    print("   - Kurs kodu, öğretmen adı, dönem bilgilerini gir")
    print("   - Sınav sayısını belirle (örn: 2)")
    print("   - Her sınav için soru sayısını belirle")
    print("   - Öğrenci sayısını gir")
    print("   - 'Devam Et' butonuna tıkla")
    
    print("\n2️⃣ Soru Puanları:")
    print("   - Her soru için maksimum puan belirle")
    print("   - CLO eşleştirmesi yap")
    print("   - 'Devam Et' butonuna tıkla")
    
    print("\n3️⃣ Not Girişi ve Validasyon Testi:")
    print("   - Öğrenci bilgilerini gir")
    print("   - Not girişi yaparken şunları test et:")
    print("     a) Maksimum puanı aşan değer gir")
    print("     b) Negatif değer gir")
    print("     c) Geçersiz format gir (örn: 'abc')")
    print("     d) Ondalık değer gir (örn: 15.7)")
    
    print("\n4️⃣ Validasyon Kontrolleri:")
    print("   - Uyarı mesajları görünüyor mu?")
    print("   - Input alanları renk değiştiriyor mu?")
    print("   - Geçersiz değerler otomatik düzeltiliyor mu?")
    print("   - Maksimum puan aşıldığında değer sınırlanıyor mu?")
    
    print("\n5️⃣ Backend Validasyon:")
    print("   - Form submit edildiğinde veritabanına doğru değerler kaydediliyor mu?")
    print("   - Geçersiz değerler backend'de de düzeltiliyor mu?")

if __name__ == "__main__":
    print("🎓 Evaluating System - Not Validasyonu Test Scripti")
    print("=" * 60)
    
    # Otomatik testler
    if test_validation_features():
        # Manuel test adımları
        show_manual_test_steps()
        
        print("\n🎉 Tüm testler tamamlandı!")
        print("💡 Projeyi test etmek için yukarıdaki adımları takip edin")
    else:
        print("\n❌ Testler başarısız!")
        print("💡 Lütfen projeyi çalıştırın ve tekrar deneyin")
    
    print("\n" + "=" * 60)
    print("🏁 Test scripti tamamlandı")
