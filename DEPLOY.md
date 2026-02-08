# Oracle Cloud 백엔드 배포 가이드

## 1. Oracle Cloud 계정 생성

1. https://cloud.oracle.com 접속
2. "무료로 시작하기" 클릭
3. 계정 생성 (신용카드 필요하지만 무료 티어는 과금 안 됨)

## 2. VM 인스턴스 생성

1. Oracle Cloud Console 접속
2. **Compute > Instances > Create Instance**
3. 설정:
   - **Image**: Ubuntu 22.04
   - **Shape**: VM.Standard.A1.Flex (Always Free)
     - OCPUs: 2
     - Memory: 12GB
   - **네트워킹**: 기본 VCN 생성
   - **SSH 키**: 새로 생성하거나 기존 키 업로드

4. 인스턴스 생성 후 **Public IP** 확인

## 3. 보안 규칙 설정

**Networking > Virtual Cloud Networks > [VCN 선택] > Security Lists**

Ingress Rules 추가:
| 포트 | 설명 |
|------|------|
| 22 | SSH |
| 8000 | Backend API |

## 4. 서버 접속 및 설정

```bash
# SSH 접속
ssh -i <your-key.pem> ubuntu@<PUBLIC_IP>

# Docker 설치
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 재로그인 (docker 그룹 적용)
exit
ssh -i <your-key.pem> ubuntu@<PUBLIC_IP>
```

## 5. 프로젝트 배포

```bash
# 프로젝트 클론
git clone <your-repo-url> sentence-space
cd sentence-space

# 환경변수 설정
cat > .env << EOF
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
EOF

# 빌드 및 실행
docker-compose -f docker-compose.prod.yml up -d --build

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f
```

## 6. 접속 확인

```bash
curl http://<PUBLIC_IP>:8000/docs
```

## 7. Vercel 프론트엔드 연결

Vercel 프로젝트 설정에서 환경변수 추가:
```
VITE_API_BASE=http://<PUBLIC_IP>:8000/api
```

## 유용한 명령어

```bash
# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 서비스 재시작
docker-compose -f docker-compose.prod.yml restart

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f backend

# 서비스 중지
docker-compose -f docker-compose.prod.yml down

# 이미지 재빌드
docker-compose -f docker-compose.prod.yml up -d --build
```
