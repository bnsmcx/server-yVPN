from typing import Tuple

digital_ocean_hourly_rate = 0.00893
yvpn_markup = 2
yvpn_hourly_rate = digital_ocean_hourly_rate * yvpn_markup
yvpn_daily_rate = yvpn_hourly_rate * 24
yvpn_minute_rate = yvpn_hourly_rate / 60


def estimate_fund_depletion(funds: float, num_endpoints: int) -> Tuple[bool, float]:
    """estimate user fund depletion at current usage"""
    daily_cost = num_endpoints * yvpn_daily_rate
    if num_endpoints:
        return True, funds / daily_cost
    return False, 0
