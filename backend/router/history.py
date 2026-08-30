from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

router = APIRouter(prefix="/historical-data", tags=["Historical Data"])

class HistoricalRecord(BaseModel):
    id: int
    record_date: date
    metric_value: float
    category: str

MOCK_DB = [
    {"id": 1, "record_date": date(2026, 1, 1), "metric_value": 105.2, "category": "temperature"},
    {"id": 2, "record_date": date(2026, 2, 1), "metric_value": 108.7, "category": "temperature"},
]

@router.get("/", response_model=List[HistoricalRecord])
def get_historical_data(
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter up to this date"),
    limit: int = Query(100, ge=1, le=1000)
):
    filtered_data = MOCK_DB
    
    if start_date:
        filtered_data = [row for row in filtered_data if row["record_date"] >= start_date]
    if end_date:
        filtered_data = [row for row in filtered_data if row["record_date"] <= end_date]
        
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    return filtered_data[:limit]