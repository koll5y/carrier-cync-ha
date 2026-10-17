# Carrier Cync (Home Assistant)

한국 캐리어 Cync 클라우드 API를 이용한 에어컨 통합입니다.  
로컬 제어 없이 `carrieriot.com` REST로 상태 조회·제어합니다. 

* 시험용입니다. (적용모델:Carrier OSQC16AAWSD)

## 설치 (HACS)

1. HACS → 우측 상단 ⋮ → **Custom repositories**
2. Repository: `YOUR_GITHUB_USERNAME/carrier-cync-ha`
3. Category: **Integration**
4. HACS에서 **Carrier Cync** 검색 후 Download
5. Home Assistant 재시작
6. 설정 → 기기 및 서비스 → 통합 추가 → **Carrier Cync**

## 설정 값

| 항목 | 예시 |
|------|------|
| Member ID | 앱 계정 ID |
| Device ID | 기기 ID (예: `8c4b14f88cb0`) |
| Device Model | `SA` |

## 기능

- Climate: 전원, 모드(냉방/난방/제습/공기청정), 희망온도
- 프리셋: PMV
- 센서: 실내온도, 실내습도 (기기 하위 엔티티)

## 한계

- 클라우드 폴링 방식이라 앱보다 상태 반영이 느릴 수 있습니다.
- 로컬 LAN 제어는 지원하지 않습니다.
