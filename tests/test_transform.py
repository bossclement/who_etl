from app.transform import transform_batch, transform_record


def test_transform_record_maps_who_fields():
    raw = {
        "SpatialDim": "USA",
        "TimeDim": 2019,
        "IndicatorCode": "WHOSIS_000001",
        "NumericValue": 72.5,
    }
    assert transform_record(raw) == {
        "country_code": "USA",
        "year": 2019,
        "indicator": "WHOSIS_000001",
        "value": 72.5,
    }


def test_transform_record_skips_missing_value():
    assert transform_record({"SpatialDim": "USA", "TimeDim": 2019}) is None


def test_transform_record_rejects_invalid_year():
    raw = {
        "SpatialDim": "USA",
        "TimeDim": 1700,
        "IndicatorCode": "WHOSIS_000001",
        "NumericValue": 1.0,
    }
    assert transform_record(raw) is None


def test_transform_batch_dedupes_within_page():
    rows = [
        {
            "SpatialDim": "FRA",
            "TimeDim": 2020,
            "IndicatorCode": "WHOSIS_000001",
            "NumericValue": 1.0,
        },
        {
            "SpatialDim": "FRA",
            "TimeDim": 2020,
            "IndicatorCode": "WHOSIS_000001",
            "NumericValue": 2.0,
        },
    ]
    result = transform_batch(rows)
    assert len(result) == 1
    assert result[0]["value"] == 2.0
