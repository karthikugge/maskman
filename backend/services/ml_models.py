"""
ml_models.py — Upgraded price intelligence and deal detection.

Improvements over the original:
- PriceIntelligenceAgent: adds confidence intervals around the linear
  regression prediction, validates inputs more robustly, and optionally
  returns a full price forecast horizon (N days).
- DealDetectionAgent: moves beyond a single hard-coded threshold by
  computing a normalised deal score [0, 1], adding a category label
  ("excellent" / "good" / "fair" / "none"), detecting all-time lows,
  and exposing the statistical context (mean, std, percentile) that
  drove the decision.
- AnomalyDetectionAgent (new): flags unusual price spikes / drops using
  a Z-score approach, useful for alerting users to sudden market changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _build_price_df(price_history: list[dict]) -> pd.DataFrame:
    """
    Convert a list of {'price': float, 'recorded_at': datetime} dicts into a
    clean, sorted DataFrame with a numeric `days` column.
    Raises ValueError for malformed input.
    """
    if not price_history:
        raise ValueError("price_history is empty.")

    df = pd.DataFrame(price_history)

    if "price" not in df.columns or "recorded_at" not in df.columns:
        raise ValueError("Each entry must have 'price' and 'recorded_at' keys.")

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])

    df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["recorded_at"]).sort_values("recorded_at").drop_duplicates("recorded_at")

    epoch = pd.Timestamp("1970-01-01", tz="utc")
    df["days"] = (df["recorded_at"] - epoch) // pd.Timedelta("1D")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class PriceForecast:
    predicted_price: Optional[float]       # None when insufficient data
    confidence_low: Optional[float]        # Lower bound of 90% CI
    confidence_high: Optional[float]       # Upper bound of 90% CI
    trend: str                             # "rising" | "falling" | "stable"
    r_squared: Optional[float]             # Model fit quality [0, 1]
    days_of_data: int
    forecast_horizon_days: list[dict] = field(default_factory=list)
    # [{"day_offset": int, "date": str, "predicted_price": float}, ...]


@dataclass
class DealAnalysis:
    is_deal: bool
    deal_score: float                      # Normalised [0, 1]; higher = better deal
    deal_category: str                     # "excellent" | "good" | "fair" | "none"
    discount_percentage: float
    is_all_time_low: bool
    current_price: float
    avg_price: float
    min_price: float
    max_price: float
    price_std: float
    price_percentile: float                # current_price percentile in history


@dataclass
class AnomalyResult:
    is_anomaly: bool
    direction: str                         # "spike" | "drop" | "none"
    z_score: float
    current_price: float
    expected_price: float                  # rolling mean at detection point
    magnitude_pct: float                   # % deviation from expected


# ---------------------------------------------------------------------------
# PriceIntelligenceAgent
# ---------------------------------------------------------------------------

class PriceIntelligenceAgent:
    """Linear regression price forecaster with confidence intervals."""

    MIN_DATA_POINTS = 3
    TREND_THRESHOLD = 0.01  # |slope| below this (price units/day) → "stable"

    @staticmethod
    def predict_future_price(
        price_history: list[dict],
        horizon_days: int = 1,
    ) -> PriceForecast:
        """
        Fit a linear regression on price history and predict the price
        `horizon_days` days from the last observation.

        Returns a `PriceForecast` dataclass that includes:
        - `predicted_price` — the point estimate
        - `confidence_low` / `confidence_high` — ~90 % prediction interval
          (based on residual standard error of the regression)
        - `trend` — "rising", "falling", or "stable"
        - `r_squared` — goodness-of-fit of the underlying linear model
        - `forecast_horizon_days` — daily predictions for each day up to
          `horizon_days`
        """
        try:
            df = _build_price_df(price_history)
        except ValueError as exc:
            logger.warning("PriceIntelligenceAgent: %s", exc)
            return PriceForecast(
                predicted_price=None,
                confidence_low=None,
                confidence_high=None,
                trend="stable",
                r_squared=None,
                days_of_data=0,
            )

        n = len(df)
        if n < PriceIntelligenceAgent.MIN_DATA_POINTS:
            logger.info(
                "PriceIntelligenceAgent: only %d data points (need %d); skipping regression.",
                n, PriceIntelligenceAgent.MIN_DATA_POINTS,
            )
            return PriceForecast(
                predicted_price=None,
                confidence_low=None,
                confidence_high=None,
                trend="stable",
                r_squared=None,
                days_of_data=n,
            )

        X = df[["days"]].values
        y = df["price"].values

        model = LinearRegression()
        model.fit(X, y)

        y_pred_train = model.predict(X)
        r2 = float(r2_score(y, y_pred_train))

        # Residual standard error → prediction interval
        residuals = y - y_pred_train
        rse = float(np.std(residuals, ddof=2)) if n > 2 else float(np.std(residuals))
        # 90% prediction interval ≈ ±1.645 * RSE (large-sample approximation)
        margin = 1.645 * rse

        slope = float(model.coef_[0])
        if slope > PriceIntelligenceAgent.TREND_THRESHOLD:
            trend = "rising"
        elif slope < -PriceIntelligenceAgent.TREND_THRESHOLD:
            trend = "falling"
        else:
            trend = "stable"

        last_day = int(df["days"].max())
        last_date = df["recorded_at"].max()

        # Build per-day forecast
        horizon_entries = []
        for offset in range(1, horizon_days + 1):
            day = last_day + offset
            raw = float(model.predict([[day]])[0])
            pred = max(0.0, round(raw, 2))
            forecast_date = (last_date + pd.Timedelta(days=offset)).date().isoformat()
            horizon_entries.append({
                "day_offset": offset,
                "date": forecast_date,
                "predicted_price": pred,
                "confidence_low": max(0.0, round(pred - margin, 2)),
                "confidence_high": round(pred + margin, 2),
            })

        main = horizon_entries[-1]

        return PriceForecast(
            predicted_price=main["predicted_price"],
            confidence_low=main["confidence_low"],
            confidence_high=main["confidence_high"],
            trend=trend,
            r_squared=round(r2, 4),
            days_of_data=n,
            forecast_horizon_days=horizon_entries,
        )


# ---------------------------------------------------------------------------
# DealDetectionAgent
# ---------------------------------------------------------------------------

class DealDetectionAgent:
    """
    Determines whether a price is a deal, with rich statistical context.

    Deal categories (based on normalised discount from historical mean):
      - excellent : ≥ 25 % below average
      - good      : 15–25 % below average
      - fair      : 5–15 % below average
      - none      : < 5 % below average  (not considered a deal)
    """

    THRESHOLDS = {
        "excellent": 0.25,
        "good":      0.15,
        "fair":      0.05,
    }

    @staticmethod
    def detect_deal(current_price: float, price_history: list[dict]) -> DealAnalysis:
        """
        Analyse whether `current_price` is a deal relative to `price_history`.

        Returns a `DealAnalysis` with the discount percentage, deal category,
        all-time-low flag, and the distributional statistics used.
        """
        prices = []
        for entry in price_history:
            try:
                prices.append(float(entry["price"]))
            except (KeyError, TypeError, ValueError):
                continue

        if not prices:
            return DealAnalysis(
                is_deal=False, deal_score=0.0, deal_category="none",
                discount_percentage=0.0, is_all_time_low=False,
                current_price=current_price, avg_price=current_price,
                min_price=current_price, max_price=current_price,
                price_std=0.0, price_percentile=100.0,
            )

        avg = float(np.mean(prices))
        std = float(np.std(prices))
        min_p = float(np.min(prices))
        max_p = float(np.max(prices))

        # What fraction of historical prices were above current_price?
        percentile = float(np.mean([p > current_price for p in prices]) * 100)

        discount_frac = (avg - current_price) / avg if avg > 0 else 0.0
        discount_frac = max(0.0, discount_frac)  # only positive discounts

        # Normalise deal score: 0 = no deal, 1 = 25%+ off average
        deal_score = round(min(1.0, discount_frac / DealDetectionAgent.THRESHOLDS["excellent"]), 4)

        if discount_frac >= DealDetectionAgent.THRESHOLDS["excellent"]:
            category = "excellent"
            is_deal = True
        elif discount_frac >= DealDetectionAgent.THRESHOLDS["good"]:
            category = "good"
            is_deal = True
        elif discount_frac >= DealDetectionAgent.THRESHOLDS["fair"]:
            category = "fair"
            is_deal = True
        else:
            category = "none"
            is_deal = False

        is_all_time_low = current_price <= min_p

        return DealAnalysis(
            is_deal=is_deal,
            deal_score=deal_score,
            deal_category=category,
            discount_percentage=round(discount_frac * 100, 1),
            is_all_time_low=is_all_time_low,
            current_price=round(current_price, 2),
            avg_price=round(avg, 2),
            min_price=round(min_p, 2),
            max_price=round(max_p, 2),
            price_std=round(std, 2),
            price_percentile=round(percentile, 1),
        )


# ---------------------------------------------------------------------------
# AnomalyDetectionAgent (new)
# ---------------------------------------------------------------------------

class AnomalyDetectionAgent:
    """
    Detects unusual price movements using Z-score analysis.

    Useful for:
    - Alerting users to sudden price spikes (seller error / surge pricing)
    - Flagging flash-sale drops before they sell out
    - Filtering out bad data before it skews forecasting models
    """

    DEFAULT_WINDOW = 7   # rolling window (in most-recent N observations)
    Z_THRESHOLD = 2.0    # |Z| above this → anomaly

    @staticmethod
    def detect(
        current_price: float,
        price_history: list[dict],
        window: int = DEFAULT_WINDOW,
        z_threshold: float = Z_THRESHOLD,
    ) -> AnomalyResult:
        """
        Compare `current_price` against the rolling statistics of
        `price_history[-window:]`.

        Returns an `AnomalyResult` with a Z-score, direction label, and
        percentage deviation from the rolling mean.
        """
        try:
            df = _build_price_df(price_history)
        except ValueError:
            return AnomalyResult(
                is_anomaly=False, direction="none", z_score=0.0,
                current_price=current_price, expected_price=current_price,
                magnitude_pct=0.0,
            )

        recent = df["price"].tail(window).values

        if len(recent) < 2:
            return AnomalyResult(
                is_anomaly=False, direction="none", z_score=0.0,
                current_price=current_price, expected_price=float(recent.mean()) if len(recent) else current_price,
                magnitude_pct=0.0,
            )

        mean = float(np.mean(recent))
        std  = float(np.std(recent, ddof=1))

        if std == 0:
            z = 0.0
        else:
            z = (current_price - mean) / std

        is_anomaly = abs(z) > z_threshold
        direction = "spike" if z > 0 else ("drop" if z < 0 else "none")
        if not is_anomaly:
            direction = "none"

        magnitude_pct = round(((current_price - mean) / mean) * 100, 1) if mean else 0.0

        return AnomalyResult(
            is_anomaly=is_anomaly,
            direction=direction,
            z_score=round(z, 3),
            current_price=round(current_price, 2),
            expected_price=round(mean, 2),
            magnitude_pct=magnitude_pct,
        )
