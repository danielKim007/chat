# -*- coding: utf-8 -*-
"""
Upbit 9 AM Pump Pattern Detector

이 스크립트는 Upbit 거래소에서 특정 암호화폐가 '오전 9시 펌핑' 패턴을 보이는지
확인하기 위해 만들어졌습니다. 이 패턴은 일반적으로 오전 9시 직전 30분 동안
거래량이 매우 적다가, 9시 정각에 거래량이 폭발적으로 증가하는 현상을 말합니다.

**주의:** 이 스크립트는 교육 및 분석 목적으로만 사용해야 합니다.
'펌핑' 패턴은 매우 위험하며, 인위적인 시세 조종일 수 있습니다.
이 정보를 기반으로 한 투자는 큰 손실을 초래할 수 있습니다.
"""
import requests
import datetime
import time

def get_krw_markets():
    """
    Upbit에서 거래 가능한 모든 KRW 마켓 목록을 가져옵니다.
    """
    url = "https://api.upbit.com/v1/market/all"
    try:
        response = requests.get(url)
        response.raise_for_status()
        markets = response.json()

        krw_markets = [m['market'] for m in markets if m['market'].startswith('KRW-')]
        print(f"업비트에서 {len(krw_markets)}개의 KRW 마켓을 찾았습니다.")
        return krw_markets
    except requests.exceptions.RequestException as e:
        print(f"마켓 목록을 가져오는 데 실패했습니다: {e}")
        return []

def check_9am_pump_pattern(market, target_date):
    """
    Upbit에서 특정 날짜의 '오전 9시 펌핑' 패턴을 감지하는 함수.
    패턴이 발견되면 상세 정보를 담은 dict를, 아니면 None을 반환합니다.

    Args:
        market (str): 확인할 마켓 코드 (예: "KRW-MVL")
        target_date (str): 확인할 날짜 (예: "2025-07-30")

    Returns:
        dict or None: 패턴 발견 시 상세 정보, 미발견 또는 에러 시 None.
    """
    # --- Constants for Pattern Detection ---
    VOLUME_SPIKE_MULTIPLIER = 20
    LOW_VOLUME_THRESHOLD_KRW = 10_000_000  # 천만원

    try:
        to_time = f"{target_date}T09:01:00%2B09:00"
        url = f"https://api.upbit.com/v1/candles/minutes/1?market={market}&to={to_time}&count=120"

        response = requests.get(url)
        if response.status_code == 404:
            # 404 에러는 마켓이 없다는 의미이므로 조용히 처리
            return None
        response.raise_for_status()

        candles = response.json()
        if not candles:
            return None

        pre_9am_volumes = []
        at_9am_volume = 0
        at_9am_price_change = 0.0

        for candle in candles:
            kst_time = datetime.datetime.fromisoformat(candle['candle_date_time_kst'])
            if kst_time.hour == 8 and 30 <= kst_time.minute <= 59:
                pre_9am_volumes.append(candle['candle_acc_trade_price'])
            if kst_time.hour == 9 and kst_time.minute == 0:
                at_9am_volume = candle['candle_acc_trade_price']
                price_open = candle['opening_price']
                price_close = candle['trade_price']
                if price_open > 0:
                    at_9am_price_change = ((price_close - price_open) / price_open) * 100

        if at_9am_volume == 0:
            return None

        avg_pre_9am_volume = sum(pre_9am_volumes) / 30

        is_low_volume = avg_pre_9am_volume < LOW_VOLUME_THRESHOLD_KRW
        is_volume_spike = (at_9am_volume > (avg_pre_9am_volume * VOLUME_SPIKE_MULTIPLIER)) if avg_pre_9am_volume > 0 else (at_9am_volume > 0)

        if is_low_volume and is_volume_spike:
            volume_ratio = at_9am_volume / avg_pre_9am_volume if avg_pre_9am_volume > 0 else float('inf')
            return {
                "market": market,
                "avg_volume_krw": avg_pre_9am_volume,
                "spike_volume_krw": at_9am_volume,
                "volume_ratio": volume_ratio,
                "price_change": at_9am_price_change
            }

        return None

    except requests.exceptions.RequestException:
        # API 요청 관련 에러는 무시하고 다음으로 넘어감
        return None
    except Exception:
        # 기타 예외 발생 시에도 다음 마켓으로 넘어감
        return None


if __name__ == "__main__":
    # --- 확인할 날짜 설정 ---
    # 특정 날짜를 확인하고 싶다면 아래 주석을 풀고 날짜를 입력하세요.
    # target_date_str = "2025-07-30"

    # 기본적으로 어제 날짜를 확인
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    target_date_str = yesterday.strftime("%Y-%m-%d")

    print(f"--- {target_date_str} 모든 KRW 마켓 펌핑 패턴 스캔 시작 ---")

    all_markets = get_krw_markets()
    found_patterns = []

    if all_markets:
        for i, market in enumerate(all_markets):
            # API 요청에 대한 약간의 지연 시간 추가 (Rate Limit 방지)
            time.sleep(0.1)
            print(f"({i+1}/{len(all_markets)}) {market} 확인 중...", end='\r')

            result = check_9am_pump_pattern(market, target_date_str)
            if result:
                found_patterns.append(result)

    print("\n--- 스캔 완료 ---")

    if found_patterns:
        # 거래량 비율(volume_ratio)이 높은 순으로 정렬
        found_patterns.sort(key=lambda x: x['volume_ratio'], reverse=True)

        print(f"\n총 {len(found_patterns)}개의 펌핑 패턴 의심 종목을 찾았습니다:")
        for p in found_patterns:
            print(f"\n- 마켓: {p['market']}")
            print(f"  - 9시 거래량 급증: {p['volume_ratio']:,.1f} 배")
            print(f"  - 1분간 가격 변동: {p['price_change']:.2f}%")
            print(f"  - 9시 거래대금: {p['spike_volume_krw']:,.0f} 원")
            print(f"  - 직전 30분 평균 거래대금: {p['avg_volume_krw']:,.0f} 원")
    else:
        print("\n펌핑 패턴이 의심되는 종목을 찾지 못했습니다.")
