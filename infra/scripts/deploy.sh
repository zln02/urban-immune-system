#!/bin/bash
# Urban Immune System — GCP 배포 스크립트
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-urban-immune-system}"
REGION="${GCP_REGION:-asia-northeast3}"
CLUSTER="${GCP_CLUSTER:-uis-cluster}"
REGISTRY="gcr.io/${PROJECT_ID}"
TAG="${GITHUB_SHA:-latest}"

echo "▶ 프로젝트: $PROJECT_ID | 리전: $REGION | 태그: $TAG"

# Docker 빌드 & 푸시
for svc in backend pipeline ml; do
  echo "▶ $svc 빌드 중..."
  docker build -t "${REGISTRY}/uis-${svc}:${TAG}" "./${svc}/"
  docker push "${REGISTRY}/uis-${svc}:${TAG}"
done

# GKE 클러스터 연결
gcloud container clusters get-credentials "$CLUSTER" --region "$REGION" --project "$PROJECT_ID"

# K8s 매니페스트 적용 (이미지 태그 치환)
for manifest in infra/k8s/*.yaml; do
  sed "s|gcr.io/PROJECT_ID|${REGISTRY}|g; s|:latest|:${TAG}|g" "$manifest" | kubectl apply -f -
done

# 롤아웃 대기
kubectl rollout status deployment/backend -n urban-immune --timeout=120s
kubectl rollout status deployment/ml -n urban-immune --timeout=180s

echo "✅ 배포 완료"
