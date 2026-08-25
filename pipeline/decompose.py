"""Fare decomposition: separate a quoted fare into base fare, statutory
taxes, User Development Fee (UDF/PSF) and OTA convenience/booking fee.

Synthetic records already arrive fully decomposed. Live-scraped pages often
only expose "Base Fare" + a single "Taxes & Fees" lump sum (or just a total),
so this module fills in the rest using the known UDF/convenience-fee tables
also used by the synthetic calibration -- those figures describe real fee
structures, not simulated ones.
"""
from scraper.synthetic import calibration


def decompose_fare(
    *,
    origin: str,
    destination: str,
    source_name: str,
    base_fare: float | None,
    total_fare: float | None,
    taxes_and_fees_lump: float | None = None,
) -> dict:
    """Returns a dict with base_fare, taxes, udf, convenience_fee, total_fare,
    all populated (or all None if there isn't enough information)."""
    if base_fare is None and total_fare is None:
        return {"base_fare": None, "taxes": None, "udf": None, "convenience_fee": None, "total_fare": None}

    udf = calibration.udf_for(origin, destination)
    convenience_fee = calibration.convenience_fee_for(source_name)

    if taxes_and_fees_lump is not None:
        # Lump sum covers statutory taxes + UDF + convenience fee together.
        taxes = round(taxes_and_fees_lump - udf - convenience_fee, 2)
    elif base_fare is not None and total_fare is not None:
        taxes = round(total_fare - base_fare - udf - convenience_fee, 2)
    elif base_fare is not None:
        taxes = calibration.taxes_for(base_fare)
    else:
        # Only a total fare is known: back out an approximate base fare using
        # the standard statutory rate, then derive taxes as the residual.
        base_fare = round((total_fare - udf - convenience_fee) / (1 + calibration.GST_RATE), 2)
        taxes = round(total_fare - base_fare - udf - convenience_fee, 2)

    # Rounding/estimation can push taxes slightly negative; clip rather than
    # propagate a nonsensical negative tax line into the clean/index layer.
    taxes = max(taxes, 0.0)

    if total_fare is None:
        total_fare = round(base_fare + taxes + udf + convenience_fee, 2)

    return {
        "base_fare": base_fare,
        "taxes": taxes,
        "udf": udf,
        "convenience_fee": convenience_fee,
        "total_fare": total_fare,
    }
