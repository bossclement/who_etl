from app.transform import transform_batch, transform_record


def test_transform_record_maps_who_fields():
    raw = {
        "SpatialDim": "USA",
        "TimeDim": 2019,
        "IndicatorCode": "WHOSIS_000001",
        "Dim1": "SEX_BTSX",
        "NumericValue": 72.5,
    }
    assert transform_record(raw) == {
        "country_code": "USA",
        "year": 2019,
        "indicator": "WHOSIS_000001",
        "sex": "SEX_BTSX",
        "value": 72.5,
    }


def test_transform_record_skips_missing_value():
    assert transform_record(
        {"SpatialDim": "USA", "TimeDim": 2019, "Dim1": "SEX_MLE"}
    ) is None


def test_transform_record_skips_missing_sex():
    assert transform_record(
        {
            "SpatialDim": "USA",
            "TimeDim": 2019,
            "IndicatorCode": "WHOSIS_000001",
            "NumericValue": 72.5,
        }
    ) is None


def test_transform_record_rejects_invalid_year():
    raw = {
        "SpatialDim": "USA",
        "TimeDim": 1700,
        "IndicatorCode": "WHOSIS_000001",
        "Dim1": "SEX_MLE",
        "NumericValue": 1.0,
    }
    assert transform_record(raw) is None


def test_transform_batch_keeps_different_sex_for_same_country_year():
    rows = [
        {
            "SpatialDim": "DNK",
            "TimeDim": 2020,
            "IndicatorCode": "WHOSIS_000001",
            "Dim1": "SEX_MLE",
            "NumericValue": 78.0,
        },
        {
            "SpatialDim": "DNK",
            "TimeDim": 2020,
            "IndicatorCode": "WHOSIS_000001",
            "Dim1": "SEX_FMLE",
            "NumericValue": 81.0,
        },
    ]
    result = transform_batch(rows)
    assert len(result) == 2
    sex_values = {row["sex"] for row in result}
    assert sex_values == {"SEX_MLE", "SEX_FMLE"}


def test_transform_batch_dedupes_exact_duplicate_keys():
    rows = [
        {
            "SpatialDim": "FRA",
            "TimeDim": 2020,
            "IndicatorCode": "WHOSIS_000001",
            "Dim1": "SEX_BTSX",
            "NumericValue": 1.0,
        },
        {
            "SpatialDim": "FRA",
            "TimeDim": 2020,
            "IndicatorCode": "WHOSIS_000001",
            "Dim1": "SEX_BTSX",
            "NumericValue": 2.0,
        },
    ]
    result = transform_batch(rows)
    assert len(result) == 1
    assert result[0]["value"] == 2.0
