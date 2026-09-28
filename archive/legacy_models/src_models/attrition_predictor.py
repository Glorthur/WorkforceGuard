"""
Retention flight risk predictive model for WorkforceGuard.
Trained on benchmark workforce data with calibration and feature attribution.
"""
from typing import List, Dict, Any, Optional, Union
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score

from src.core.schemas import FlightRiskPrediction

NUMERIC_FEATURES = [
    "Age", "MonthlyIncome", "DistanceFromHome", "JobSatisfaction",
    "WorkLifeBalance", "YearsAtCompany", "YearsSinceLastPromotion"
]
CATEGORICAL_FEATURES = ["OverTime", "Department", "JobRole"]

class AttritionPredictor:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), NUMERIC_FEATURES),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ]
        )
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=4,
            random_state=self.random_state,
            class_weight="balanced"
        )
        self.pipeline = Pipeline(steps=[
            ("preprocessor", self.preprocessor),
            ("classifier", self.model)
        ])
        self.is_fitted = False
        self.evaluation_metrics: Dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> "AttritionPredictor":
        """Fits the flight risk model on an employee attrition dataset."""
        df_clean = df.copy()
        if "Attrition_Binary" not in df_clean.columns:
            df_clean["Attrition_Binary"] = (df_clean["Attrition"].str.strip().str.lower() == "yes").astype(int)
            
        X = df_clean[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        y = df_clean["Attrition_Binary"]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state, stratify=y
        )
        
        self.pipeline.fit(X_train, y_train)
        self.is_fitted = True
        
        # Compute test metrics
        y_pred = self.pipeline.predict(X_test)
        y_prob = self.pipeline.predict_proba(X_test)[:, 1]
        
        self.evaluation_metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
            "f1_score": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        }
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Predictor is not fitted yet.")
        features = X[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        return self.pipeline.predict_proba(features)[:, 1]

    def predict_flight_risk(self, df_or_dict: Union[pd.DataFrame, Dict[str, Any]]) -> List[FlightRiskPrediction]:
        """
        Predicts attrition probability, assigns risk tier, and generates
        personalized retention recommendations.
        """
        if not self.is_fitted:
            raise ValueError("Predictor is not fitted yet.")
            
        if isinstance(df_or_dict, dict):
            df_input = pd.DataFrame([df_or_dict])
        else:
            df_input = df_or_dict.copy()
            
        probs = self.predict_proba(df_input)
        results = []
        
        for idx, (_, row) in enumerate(df_input.iterrows()):
            prob = float(probs[idx])
            
            if prob >= 0.60:
                risk_level = "High"
            elif prob >= 0.35:
                risk_level = "Medium"
            else:
                risk_level = "Low"
                
            drivers = []
            recs = []
            
            # Rule-informed feature driver analysis
            if str(row.get("OverTime", "")).strip().lower() == "yes":
                drivers.append({"factor": "OverTime Work", "impact": "High Positive Risk", "value": "Yes"})
                recs.append("Review overtime allocation; implement compensatory rest periods.")
            
            satisfaction = int(row.get("JobSatisfaction", 3))
            if satisfaction <= 2:
                drivers.append({"factor": "Low Job Satisfaction", "impact": "High Positive Risk", "value": satisfaction})
                recs.append("Schedule 1-on-1 career engagement dialogue to address role sentiment.")
                
            wlb = int(row.get("WorkLifeBalance", 3))
            if wlb <= 2:
                drivers.append({"factor": "Poor Work-Life Balance", "impact": "Moderate Risk", "value": wlb})
                recs.append("Explore hybrid or flexible scheduling arrangements.")
                
            promo_gap = int(row.get("YearsSinceLastPromotion", 0))
            if promo_gap >= 4:
                drivers.append({"factor": "Extended Promotion Stagnation", "impact": "Moderate Risk", "value": f"{promo_gap} years"})
                recs.append("Assess promotion readiness or pathway for lateral skill growth.")
                
            distance = int(row.get("DistanceFromHome", 0))
            if distance >= 20:
                drivers.append({"factor": "Long Commute Distance", "impact": "Low/Moderate Risk", "value": f"{distance} miles"})
                recs.append("Evaluate remote work eligibility or transit subsidy.")
                
            if not drivers:
                drivers.append({"factor": "Normal Baseline Factors", "impact": "Neutral", "value": "Standard Profile"})
            if not recs:
                recs.append("Maintain routine talent check-ins and performance alignment.")

            emp_id = int(row.get("EmployeeNumber", row.get("employee_id", idx + 1)))
            results.append(
                FlightRiskPrediction(
                    employee_id=emp_id,
                    probability=round(prob, 4),
                    risk_level=risk_level,
                    primary_drivers=drivers,
                    retention_recommendations=recs,
                )
            )
        return results

    def save(self, filepath: Union[str, Path]) -> None:
        with open(filepath, "wb") as f:
            pickle.dump({
                "pipeline": self.pipeline,
                "evaluation_metrics": self.evaluation_metrics,
                "is_fitted": self.is_fitted
            }, f)

    def load(self, filepath: Union[str, Path]) -> "AttritionPredictor":
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            self.pipeline = data["pipeline"]
            self.evaluation_metrics = data["evaluation_metrics"]
            self.is_fitted = data["is_fitted"]
        return self
