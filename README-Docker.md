# Docker ile Evaluating System Kurulumu

## 🐳 Docker Kurulumu

### 1. Docker Image Oluşturma
```bash
# Docker image'ı build et
docker build -t evaluating-system .

# Image'ı kontrol et
docker images | grep evaluating-system
```

### 2. Docker Container Çalıştırma
```bash
# Container'ı çalıştır
docker run -d -p 8080:8080 --name evaluating-system evaluating-system

# Container durumunu kontrol et
docker ps
```

### 3. Docker Compose ile Çalıştırma (Önerilen)
```bash
# Uygulamayı başlat
docker-compose up -d

# Logları görüntüle
docker-compose logs -f

# Uygulamayı durdur
docker-compose down
```

## 🌐 Erişim
- **URL:** http://localhost:8080
- **Port:** 8080

## 📁 Veri Kalıcılığı
- Veritabanı `./instance` klasöründe saklanır
- Docker volume ile kalıcı hale getirilir

## 🔧 Docker Komutları

### Container Yönetimi
```bash
# Container'ı durdur
docker stop evaluating-system

# Container'ı başlat
docker start evaluating-system

# Container'ı yeniden başlat
docker restart evaluating-system

# Container'ı sil
docker rm evaluating-system
```

### Image Yönetimi
```bash
# Image'ı sil
docker rmi evaluating-system

# Tüm kullanılmayan image'ları temizle
docker image prune -a
```

## 🚀 Production Deployment
```bash
# Production için build
docker build -t evaluating-system:latest .

# Production'da çalıştır
docker run -d \
  -p 8080:8080 \
  --name evaluating-system \
  --restart unless-stopped \
  -v $(pwd)/instance:/app/instance \
  evaluating-system:latest
```

## 📝 Notlar
- İlk çalıştırmada veritabanı otomatik oluşturulur
- Port 8080 kullanılır (değiştirilebilir)
- Veritabanı verileri `./instance` klasöründe saklanır
