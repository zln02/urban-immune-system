from otc_collector import collect_otc_data
from search_collector import collect_search_trends
from wastewater import collect_wastewater_data
from weather_collector import collect_weather_data


def build_payload() -> list[dict]:
    return (
        collect_otc_data()
        + collect_wastewater_data()
        + collect_search_trends()
        + collect_weather_data()
    )


def main() -> None:
    payload = build_payload()
    print(f"Prepared {len(payload)} signals for Kafka publish")


if __name__ == "__main__":
    main()
