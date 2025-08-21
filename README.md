# Evaluating System - Öğrenci Not Değerlendirme Sistemi

## Proje Hakkında

Bu proje, öğrenci notlarını değerlendirmek ve analiz etmek için geliştirilmiş kapsamlı bir web uygulamasıdır. Sistem, öğrenci notlarını girerken maksimum puan sınırlarını kontrol eder ve kullanıcı dostu bir arayüz sunar.

## Özellikler

### 🎯 Ana Özellikler
- **Kurs Yönetimi**: Kurs oluşturma, düzenleme ve silme
- **Sınav Yönetimi**: Çoklu sınav ekleme ve yapılandırma
- **Öğrenci Yönetimi**: Öğrenci bilgilerini girme ve düzenleme
- **Not Girişi**: Soru bazında not girişi ve validasyon
- **CLO (Course Learning Outcomes) Analizi**: Bloom taksonomisi ile öğrenme çıktıları analizi
- **Performans Analizi**: İstatistiksel analiz ve raporlama

### 🔒 Not Validasyonu (YENİ!)
- **Maksimum Puan Kontrolü**: Her soru için maksimum puanı aşmayı engeller
- **Gerçek Zamanlı Validasyon**: Anlık kontrol ve uyarılar
- **Görsel Geri Bildirim**: Renk kodlu input alanları
- **Otomatik Düzeltme**: Geçersiz değerleri otomatik olarak düzeltir

### 📊 Raporlama
- **Öğrenci Performansı**: Bireysel öğrenci analizi
- **Soru Analizi**: Soru bazında performans değerlendirmesi
- **CLO Skorları**: Öğrenme çıktıları analizi
- **İstatistiksel Özet**: Ortalama, medyan, min-max değerler

## Kurulum

### Gereksinimler
- Python 3.7+
- Flask
- SQLAlchemy
- Pandas
- NumPy
- OpenPyXL

### Kurulum Adımları
1. Projeyi klonlayın:
```bash
git clone <repository-url>
cd "Evaluating system"
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python gui_evaluating.py
```

4. Tarayıcınızda `http://localhost:8080` adresine gidin

## Kullanım

### 1. Kurs Oluşturma
- Ana sayfada kurs bilgilerini girin
- Sınav sayısını ve her sınavdaki soru sayısını belirleyin
- Öğrenci sayısını girin

### 2. Soru Puanları
- Her soru için maksimum puan belirleyin
- CLO (Course Learning Outcomes) eşleştirmesi yapın

### 3. Öğrenci Notları
- Öğrenci bilgilerini girin
- Her soru için not girin (maksimum puanı aşamaz)
- Sistem otomatik olarak geçersiz değerleri düzeltir

### 4. Analiz ve Raporlama
- Bloom taksonomisi analizi
- CLO skorları hesaplama
- Performans istatistikleri

## Not Validasyonu Detayları

### Frontend Validasyonu
- **Gerçek Zamanlı Kontrol**: Her karakter girişinde kontrol
- **Maksimum Puan**: Soru puanını aşmayı engeller
- **Negatif Değer**: Negatif not girişini engeller
- **Ondalık Hassasiyet**: 0.1 hassasiyetinde yuvarlama

### Backend Validasyonu
- **Çift Kontrol**: Frontend ve backend'de ayrı ayrı kontrol
- **Veritabanı Güvenliği**: Geçersiz verilerin kaydedilmesini engeller
- **Otomatik Düzeltme**: Geçersiz değerleri otomatik olarak düzeltir

### Görsel Geri Bildirim
- **Yeşil**: Geçerli değer
- **Kırmızı**: Hatalı değer
- **Turuncu**: Uyarı (maksimum puan aşıldı)
- **Mavi**: Odaklanmış alan

## Teknik Detaylar

### Veritabanı Yapısı
- **Course**: Kurs bilgileri
- **Exam**: Sınav bilgileri
- **Question**: Soru detayları ve maksimum puanlar
- **Student**: Öğrenci bilgileri
- **Grade**: Not kayıtları
- **CLO**: Öğrenme çıktıları

### API Endpoints
- `POST /save_exam_data`: AJAX ile not kaydetme
- `GET/POST /student_grades`: Not girişi sayfası
- `GET /summary`: Özet rapor sayfası

### Güvenlik Özellikleri
- Session tabanlı kimlik doğrulama
- Input validasyonu
- SQL injection koruması
- XSS koruması

## Geliştirme

### Kod Yapısı
- **MVC Pattern**: Model-View-Controller mimarisi
- **Modüler Yapı**: Ayrı modüller halinde organize edilmiş
- **Responsive Design**: Mobil uyumlu arayüz

### Test Etme
1. Uygulamayı başlatın
2. Test kursu oluşturun
3. Not girişi yaparken validasyonu test edin
4. Maksimum puanı aşmaya çalışın
5. Negatif değer girmeye çalışın

## Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit yapın (`git commit -m 'Add some AmazingFeature'`)
4. Push yapın (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## İletişim

Proje hakkında sorularınız için issue açabilir veya geliştirici ile iletişime geçebilirsiniz.

## Sürüm Geçmişi

### v2.0.0 (Güncel)
- ✅ Not validasyonu eklendi
- ✅ Maksimum puan kontrolü
- ✅ Gerçek zamanlı uyarılar
- ✅ Görsel geri bildirim
- ✅ Backend güvenlik kontrolleri

### v1.0.0
- ✅ Temel not girişi
- ✅ CLO analizi
- ✅ Performans raporlama
- ✅ Veritabanı yönetimi
